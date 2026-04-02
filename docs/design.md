# jsmn-tools Design Notes

A Python code generator for JSON parsing in C using jsmn. This document captures
design decisions and lessons learned from prior implementations (schema_tools in
Rust, prototype in TypeScript).

## Background

We are rewriting schema_tools (Rust + CBOR) as jsmn-tools (Python + JSON). The
core challenge remains: transforming OpenAPI specs into C code that can
parse/serialize JSON without heap allocation.

## Pain Points from Prior Implementations

**$ref Resolution (Rust)** — The Rust implementation built a custom YAML parser
and had to manually resolve `$ref` chains, leading to complex linking logic and
error handling.

**No Standard Parser (Rust)** — Without a battle-tested OpenAPI parser, edge
cases in spec handling became bugs.

**Iterator Boilerplate (Rust)** — Rust's ownership model required verbose
iterator implementations for tree traversal.

**JS Ecosystem Overhead (TypeScript prototype)** — A TypeScript prototype used
`@scalar/json-magic` for `$ref` resolution and bundling. Lessons learned:

- Scalar's tooling is purpose-built for their API reference viewer (reactive UI
  with lazy proxy-based ref resolution). Our use case—static codegen—needs
  eagerly resolved plain dicts, which Scalar doesn't natively produce.
- The only Scalar API we actually used was `bundle()`, a generic JSON `$ref`
  resolver with no OpenAPI awareness. The OpenAPI-specific `join()` was
  convenience at best.
- `swagger-parser` (the other major option) has been largely unmaintained since
  ~2021 and has incomplete OpenAPI 3.1 / `$prefixItems` support.
- The core algorithm—walk a YAML tree, follow `$ref` pointers, inline targets—is
  ~50 lines in any language. Pulling in an npm dependency chain for this added
  build complexity (dual JS/Python tooling, npm + pip, intermediate artifact
  hand-off) without proportional value.
- Python has `pyyaml` for YAML and `pathlib` for file loading. `$ref` resolution
  is JSON pointer arithmetic—no library needed.

## Key Insight

`$ref` resolution for our workspace use case is straightforward: load YAML
files, follow JSON pointers, rewrite refs to standard relative-file format. No
URL fetching, no proxy objects, no reactive framework integration. Python
handles this directly.

```
Workspace → Scan → Rewrite → Collect → Validate → Flatten → Codegen → C
```

One language, one toolchain. Discovery, ref rewriting, validation, flattening,
and codegen all live in Python.

## C Constraints

C has no heap (in our embedded context), no nested type definitions, and
requires forward declaration. The IR must account for:

| Constraint              | OpenAPI                | C Representation                          |
| ----------------------- | ---------------------- | ----------------------------------------- |
| No unbounded strings    | `type: string`         | Requires `maxLength` → `uint8_t[N]`       |
| No unbounded arrays     | `type: array`          | Requires `maxItems` → fixed or VLA struct |
| No nested types         | Inline objects         | Flatten to top-level structs              |
| Forward declaration     | Any order in spec      | Emit dependencies first                   |
| No optional primitive   | `required` omitted     | Wrapper struct with presence flag         |
| Fixed vs dynamic arrays | `minItems == maxItems` | `T[N]` vs `struct { len; T items[N]; }`   |

## IR Design

The IR is a flat list of descriptors. Each descriptor is **one level
deep**—fields are either primitives or references to other named descriptors.

Nested objects become separate descriptors, each requiring an explicit
`x-st-generate` marker:

- `user.meta.tags[].label` becomes descriptors for `user`, `meta`, `tag` (or
  whatever names the author assigns via `x-st-generate`)
- Parent references child via `RefType` using the child's assigned name
- Unmarked nested objects are an error—the author must explicitly name them

This flattening mirrors how C structs must be organized.

## Dependency Ordering

C requires types to be declared before use. Specs can define schemas in any
order.

**Solution**: Recursive emit with caching.

```
emit(descriptor):
  if cached(descriptor): return
  for each field that refs another descriptor:
    emit(that descriptor)        ← recurse into deps first
  output(descriptor)
  cache(descriptor)
```

No topological sort needed. The recursion naturally ensures dependencies appear
before dependents. The cache prevents duplicate emissions.

## Optional Field Handling

Fields not in the `required` array need presence tracking at runtime. C pattern:

```c
struct optional__T {
    bool present;
    union { T value; } maybe;
};
```

The IR marks each field as `required: boolean`. Codegen emits wrapper types as
needed.

## Variable Length Arrays

When `minItems != maxItems`, the array length is dynamic. C pattern:

```c
struct vla__T_N {
    uint32_t len;
    uint8_t _pad[4];  // align items to 8-byte boundary
    T items[N];       // N = maxItems (capacity)
};
```

When `minItems == maxItems`, it's a fixed array: `T items[N]`.

The IR captures both bounds; codegen decides representation.

## Discovery

Discovery scans a workspace for jsmn-tools modules, builds a registry of
cross-module references, and outputs a set of OpenAPI files with all workspace
refs rewritten to standard relative-file format.

### Design Goals

1. **Codegen correctness** — Walk all schemas, validate constraints, emit C
2. **External tool compatibility** — Output valid OpenAPI that Redoc, Scalar,
   Stoplight, and linters can consume

### Output: Adjacent Files

The output is a **destination folder** containing one OpenAPI file per module.
All resources within a module are merged into a single file. Workspace `$ref`
pointers are rewritten to relative file paths:

```
Source workspace:
  sdk/.jsmn-tools.yaml               (declares resources: auth, common)
  sdk/schemas/auth.openapi.yaml      ($ref: 'network:http#/...')
  sdk/schemas/common.openapi.yaml
  network/.jsmn-tools.yaml           (declares resources: http)
  network/schemas/http.openapi.yaml

Output folder:
  output/sdk.openapi.yaml            (merged auth + common, $ref: './network.openapi.yaml#/...')
  output/network.openapi.yaml
```

Each output file is a standalone valid OpenAPI document. Modern tools (Redoc,
Scalar, Stoplight) handle multi-file specs with relative `$ref` natively.

### Decoupled from West

The prior Python implementation was coupled to Zephyr's `west` manifest API for
enumerating projects. Discovery here takes a simpler input: an array of root
directory paths. A Zephyr integration would get these paths from `west`; a
standalone project would pass them directly. Discovery doesn't care where the
paths came from.

### Config Files and Scheme Registry

Each root directory may contain a `.jsmn-tools.yaml` (or variant:
`JsmnForge.yml`, `.jsmnForge.yaml`, etc.). This file declares a module **name**
and its **resources**—named groups of OpenAPI spec files that belong together.

```yaml
name: atx-zdk
resources:
  - name: common
    version: 0
    specs:
      - schemas/common.openapi.yaml
    if:
      - CONFIG_COMMON_ENABLE
```

Each resource has a name, version, a list of spec file paths, optional
Kconfig-style guards (`if`), and optional template mappings for codegen.

Discovery scans the full directory array, loads every `.jsmn-tools.yaml` it
finds, and builds a flat **scheme registry**—one pass, no ordering, no
entrypoint. Each config's name becomes a URI scheme, and its resources become
the spec map under that scheme.

```
Registry:
  atx-zdk:common  → C:/workspace/sdk/schemas/common.openapi.yaml
  netway:http     → C:/workspace/netway/schemas/http.openapi.yaml
```

With the registry in place, spec authors reference cross-module schemas by
scheme name rather than filesystem path:

```yaml
$ref: "atx-zdk:common#/components/schemas/DeviceStatus"
```

This reads as: scheme `atx-zdk`, resource `common`, JSON pointer
`#/components/schemas/DeviceStatus`. The author never knows where `atx-zdk`
lives on disk. If a module moves, only the directory array changes—no specs are
edited.

### $ref Rewriting

Resolution rewrites `$ref` pointers to standard relative-file format. When the
walker encounters a `$ref`:

- **Local pointer** (`#/components/schemas/Foo`) — unchanged
- **Workspace reference** (`module:resource#/path`) — rewritten to relative file
  path: `./module.openapi.yaml#/path` (resource component is dropped; the JSON
  pointer still resolves in the merged output)
- **URL reference** (`https://...`) — left as-is (external tools can fetch)

After rewriting, all custom URI schemes are gone. Each output file is a
standalone valid OpenAPI document with standard `$ref` syntax.

### Output File Naming

Files are named by module:

```
{module}.openapi.yaml
```

Examples:

- `sdk` (resources: auth, common) → `sdk.openapi.yaml`
- `network` (resources: http) → `network.openapi.yaml`

Module names are unique by registry construction, so file name collisions are
impossible.

### Merge Conflicts

When merging resources within a module, conflicts may arise. All conflicts are
collected (not fail-fast) and reported together before aborting. No silent
merges or race conditions.

| Conflict                     | Severity   | Handling                                 |
| ---------------------------- | ---------- | ---------------------------------------- |
| `openapi` version mismatch   | Hard error | Can't safely merge 3.0 and 3.1           |
| `info.title` mismatch        | Collect    | Report all values, resolve via config    |
| `info.version` mismatch      | Collect    | Report all values, resolve via config    |
| `paths` (same path + method) | Collect    | List conflicting resources               |
| `components/*` (same key)    | Collect    | List conflicting resources               |
| `x-st-generate` collision  | Collect    | List conflicting schemas                 |
| `servers`, `tags`            | —          | Merge with deduplication (by url / name) |

**Example output:**

```
Errors:
  - OpenAPI version mismatch: auth uses 3.1.0, common uses 3.0.3
    (All specs must use the same OpenAPI version)

Conflicts (resolve before bundling):
  - info.title differs:
      auth: "Auth API"
      common: "Common API"
    → Specify unified title in bundle config

  - info.version differs:
      auth: "2.1.0"
      common: "1.4.2"
    → Specify unified version in bundle config
```

**Resolution via config:**

```yaml
# .jsmn-tools.yaml
bundle:
  info:
    title: "Unified Embedded API"
    version: "3.0.0"
```

When `bundle.info` is specified, `info.title`/`info.version` mismatches are
resolved using the config values instead of erroring.

### Flag Filtering

Resources can be conditionally enabled via the `if` field. The caller passes a
flat key-value map of flags (booleans, numbers, strings). If any flag in the
`if` list is truthy in the map, the resource is included. This decouples
filtering from any specific config system—Zephyr's `autoconf.h`, CMake cache
variables, or a plain JSON file all work.

### Type Extraction

Codegen is driven exclusively by the `x-st-generate` extension. A schema node
is codegen'd if and only if it carries `x-st-generate`. The extension value is
a string that supports interpolation with `${keyword}` placeholders. Currently
one keyword is defined:

| Keyword | Resolves to                                                                  |
| ------- | ---------------------------------------------------------------------------- |
| `${id}` | The context-derived identifier (e.g., schema key under `components.schemas`) |

Using `${id}` where no context name can be derived is an error.

```yaml
# Inherit schema key → codegen'd as "device_info"
components:
  schemas:
    device_info:
      x-st-generate: ${id}
      type: object
      properties:
        serial:
          type: string
          maxLength: 32

# Literal name (no context needed) → codegen'd as "reboot_cmd"
requestBody:
  content:
    application/json:
      schema:
        x-st-generate: reboot_cmd
        type: object
        properties:
          delay_s:
            type: integer
            format: uint16
```

Schemas without `x-st-generate` are ignored by codegen—they exist as API
documentation only.

### Pipeline

```
Workspace Modules
       │
       ▼
┌─────────────────┐
│  SCAN + PARSE   │  (find .jsmn-tools.yaml, load specs)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     FILTER      │  (evaluate if: guards)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MERGE + REWRITE │──────────────► Output folder (multi-file OpenAPI)
└────────┬────────┘                - One file per module
         │                         - Workspace refs → relative file refs
         │                         - x-st-generate preserved
         ▼
┌─────────────────┐
│    COLLECT      │  (filter by x-st-generate)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    VALIDATE     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    FLATTEN      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    CODEGEN      │──────────────► .h / .c files
└─────────────────┘
```

#### Step 1: Scan + Parse

Walk each root path looking for config files. Load each config and its
referenced OpenAPI specs as YAML dicts.

#### Step 2: Filter

Evaluate `if` guards against the caller-supplied flag map. Discard disabled
resources.

#### Step 3: Merge + Rewrite

For each module:

1. Merge all resources into a single OpenAPI document (see Merge Conflicts)
2. Walk the tree looking for `$ref` nodes
3. If workspace ref (`module:resource#/path`), rewrite to
   `./module.openapi.yaml#/path`
4. Write the merged spec to the output folder as `{module}.openapi.yaml`

The output folder contains valid OpenAPI files with no custom URI schemes.

#### Step 4: Collect

Walk all output files. For each schema with `x-st-generate`, record the
mapping:

```
file + json_path → C type name
sdk.openapi.yaml#/components/schemas/auth_token → auth_token
```

**Error: name collision** — if two schemas resolve to the same C type name:

```
Error: C type name 'widget' used by multiple schemas:
  - sdk.openapi.yaml#/components/schemas/widget
  - network.openapi.yaml#/components/schemas/gadget
```

#### Step 5: Validate

For each collected schema, validate codegen constraints:

| Check                               | Error                                                                   |
| ----------------------------------- | ----------------------------------------------------------------------- |
| Property refs unmarked complex type | `'config.meta' refs unmarked complex type. Add x-st-generate.`        |
| `oneOf`/`anyOf` variant unmarked    | `'response' oneOf variant is unmarked. All variants need x-jsmn-tools.` |
| `${id}` without context             | `${id} used but no context identifier available. Use a literal name.`   |
| Recursive type detected             | `Recursive type 'person' detected. Not supported.`                      |

#### Step 6: Flatten

Convert each validated schema to an IR descriptor:

- **Ref to marked schema** → `RefType` with the target's C type name
- **Ref to unmarked primitive** → inline the primitive type
- **`allOf`** → merge fields from all branches into one descriptor
- **`oneOf`/`anyOf`** → tagged union with `RefType` variants

#### Step 7: Codegen

Emit C code from the IR using Jinja templates. Dependency ordering ensures
referenced types are declared before use.

### Schema Locations

The walker must visit every location where a JSON Schema can appear in OpenAPI
3.1:

**Tier 1: Primary Targets**

| Path Pattern                                                       | Description                 |
| ------------------------------------------------------------------ | --------------------------- |
| `components/schemas/{name}`                                        | Reusable schema definitions |
| `paths/{path}/{method}/requestBody/content/{media}/schema`         | Request body                |
| `paths/{path}/{method}/responses/{code}/content/{media}/schema`    | Response body               |
| `webhooks/{name}/{method}/requestBody/content/{media}/schema`      | Webhook request             |
| `webhooks/{name}/{method}/responses/{code}/content/{media}/schema` | Webhook response            |

**Tier 2: Reusable Components**

| Path Pattern                                             | Description           |
| -------------------------------------------------------- | --------------------- |
| `components/responses/{name}/content/{media}/schema`     | Reusable response     |
| `components/requestBodies/{name}/content/{media}/schema` | Reusable request body |
| `components/parameters/{name}/schema`                    | Reusable parameter    |
| `components/headers/{name}/schema`                       | Reusable header       |

**Tier 3: Inline in Operations**

| Path Pattern                                                   | Description                |
| -------------------------------------------------------------- | -------------------------- |
| `paths/{path}/{method}/parameters[]/schema`                    | Inline operation parameter |
| `paths/{path}/parameters[]/schema`                             | Path-level parameter       |
| `paths/{path}/{method}/responses/{code}/headers/{name}/schema` | Response header            |

**Tier 4: Deferred**

| Path Pattern                                                 | Rationale               |
| ------------------------------------------------------------ | ----------------------- |
| `paths/{path}/{method}/callbacks/{name}/{expr}/{method}/...` | Recursive, rare         |
| `components/pathItems/{name}/...`                            | OpenAPI 3.1 only, rare  |
| `encoding/{property}/headers/{name}/schema`                  | Multipart edge case     |
| `parameters[]/content/{media}/schema`                        | Complex parameter media |

**Nested Within Schemas** (handled during flatten):

`properties`, `items`, `additionalProperties`, `allOf`, `oneOf`, `anyOf`, `not`,
`if`/`then`/`else`, `prefixItems`, `contains`, `propertyNames`,
`dependentSchemas`, `patternProperties`, `unevaluatedProperties`,
`unevaluatedItems`

### Edge Cases

| Case | Scenario                       | Handling                                 |
| ---- | ------------------------------ | ---------------------------------------- |
| 1    | Marked refs marked             | `RefType` with target's name ✓           |
| 2    | Marked refs unmarked primitive | Inline as primitive ✓                    |
| 3    | Marked refs unmarked object    | **Error** — author must mark it          |
| 4    | `oneOf` all marked             | Tagged union ✓                           |
| 5    | `oneOf` has unmarked           | **Error** — all variants must be marked  |
| 6    | `allOf` branches               | Merge fields (regardless of marking) ✓   |
| 7    | C type name collision          | **Error** — list conflicting schemas     |
| 8    | Recursive types                | **Error** — pointers viable but deferred |
| 9    | `${id}` in anonymous position  | **Error** — use literal name             |

### External Tool Compatibility

| Tool              | Multi-File Support | Notes                             |
| ----------------- | ------------------ | --------------------------------- |
| Redoc / Redocly   | ✓                  | Handles relative `$ref` natively  |
| Scalar            | ✓                  | Uses internal bundler             |
| Stoplight         | ✓                  | Supports `./file.yaml#/path`      |
| Swagger UI        | ⚠                  | Partial; CORS issues cross-origin |
| Spectral (linter) | ✓                  | Full multi-file support           |

For Swagger UI users, provide optional `--bundle` flag that produces a single
file (see Bundling Strategies below).

## Bundling Strategies

Each module may declare multiple resources (spec files). The merge step combines
these into a single OpenAPI document per module, producing one output file per
module with workspace refs rewritten to relative file paths.

```
output/
  sdk.openapi.yaml           (merged: auth + common)
  network.openapi.yaml       → $ref: './sdk.openapi.yaml#/...'
```

Module names are unique by registry construction, so file collisions are
impossible. Modern tools (Redoc, Scalar, Stoplight, Spectral) handle multi-file
specs with relative `$ref` natively. For legacy tools that require a single
file, a `--bundle` flag produces a single-file output with prefixed schema keys
to avoid cross-module name collisions.

### Resource Merge Algorithm

When a module has multiple resources, their specs are merged into one document.
The implementation is a two-step process: normalize, then merge.

1. **Normalize** — Walk the spec tree using context-aware transition functions.
   Each position in the document has a transition that knows the structural
   role of its children (OpenAPI object, map, JSON Schema, or opaque data).
   Set-like arrays are sorted using sort keys provided by the transition
   tables, making array comparison deterministic regardless of authoring order.

2. **Merge** — Recursive deep merge of two normalized specs. The algorithm
   dispatches on value type:
   - **Dicts**: recurse into shared keys; deep-copy keys present only in
     source.
   - **Sorted arrays** (transition provides a sort key): union merge using the
     sort key as identity. Duplicate identities with differing values are
     recorded as conflicts.
   - **Ordered arrays** (no sort key): positional merge with recursion on
     differing elements; source tail is appended.
   - **Scalars**: conflict if values differ.

   Conflicts are collected as `MergeConflict` objects (location, destination
   value, source value) rather than raised as exceptions. A `ConflictPolicy`
   (KEEP or REPLACE) controls resolution — default is KEEP (base wins).

### Context-Aware Array Handling

The transition tables encode which arrays are order-independent sets and what
identity function to use for each. Normalize sorts these arrays before merge,
and merge uses the sort key for identity-based union semantics. Ordered arrays
(no sort key) use positional comparison.

The following OpenAPI 3.1 / JSON Schema 2020-12 array fields are
order-independent (set semantics):

| Field                      | Parent Object              | Sort Key           |
| -------------------------- | -------------------------- | ------------------ |
| `required`                 | Schema Object              | string             |
| `enum`                     | Schema Object              | canonical          |
| `enum`                     | Server Variable Object     | string             |
| `type` (array form)        | Schema Object              | string             |
| `dependentRequired` values | Schema Object              | string             |
| `examples`                 | Schema Object              | canonical          |
| `security`                 | OpenAPI Object / Operation | canonical          |
| scope arrays               | Security Requirement Object| string             |
| `parameters`               | Path Item / Operation      | `(in, name)` tuple |
| `tags`                     | Operation Object           | string             |
| `allOf`                    | Schema Object              | canonical          |
| `oneOf`                    | Schema Object              | canonical          |
| `anyOf`                    | Schema Object              | canonical          |

Order-dependent arrays (no sort key, positional merge): `servers` (first is
de facto default), root-level `tags` (spec says order reflects display),
`prefixItems` (positional schema application).

## OpenAPI Feature Support

| Feature                         | Status      | Notes                                                    |
| ------------------------------- | ----------- | -------------------------------------------------------- |
| `nullable: true` (3.0)          | ✓ Supported | Maps to `optional__T` wrapper                            |
| `type: [..., "null"]` (3.1)     | ✓ Supported | Same — normalized to optional                            |
| `$ref` with siblings            | ✓ Supported | Treated as implicit `allOf`, merge fields                |
| `format` (uint8, int32, etc.)   | ✓ Supported | Required for integer/number types                        |
| `pattern`, `minimum`, `maximum` | ✓ Captured  | Passed to IR as metadata; no runtime validation yet      |
| `readOnly` / `writeOnly`        | ✓ Captured  | Passed to IR as metadata; future: separate encode/decode |
| `additionalProperties`          | ⚠ Warn      | Requires heapless map; not implemented                   |
| `patternProperties`             | ⚠ Warn      | Requires heapless map; not implemented                   |
| Recursive types                 | ✗ Error     | Pointers viable but out of scope                         |
| `type: integer` (no format)     | ⚠ Warn      | Defaults to int32                                        |
| `type: string` (no maxLength)   | ✗ Error     | C strings require bounds                                 |

## Name Mangling

Generated C types for VLA, optional, and fixed-dimension wrappers need globally
unique, deterministic identifiers. The name encodes type structure because these
are shared library primitives—an `optional__u32` is not tied to any particular
struct field, it is the canonical optional wrapper for `uint32_t` reused
wherever needed. Codegen has no application context to derive names from.

Schema authors can override any generated name with `x-st-generate` on the
schema node.

Mangling is a **codegen responsibility**, not a parser responsibility. The IR
carries structural type descriptors; codegen derives C identifiers from them.
This keeps C-specific naming out of the parser so the same IR can drive other
backends (e.g., TypeScript bindings for client-side code sharing the same schema
types).

### Mangling Rules

Compiler manglers (Itanium, Rust v0) use single-character delimiters for
unambiguous nesting but are unreadable. C code generators (protobuf-c) use `__`
separators for readability but don't handle parametric types. We use `__` as a
uniform wrapper boundary with **letter-tagged values** to disambiguate:

- **`__`** (double underscore) — separates all structural boundaries (wrapper
  prefixes, tags, and modifiers from the base type)
- **`_`** (single underscore) — only appears within user-defined struct names
  (e.g., `thing_nested`) and within multi-dimension groups joined by `x`

This uniform rule means `__` always signals a structural boundary regardless of
the base type's content. A VLA of `u32` and a VLA of `thing_foo` use the same
separator pattern: `vla__u32__n3`, `vla__thing_foo__n3`.

**Primitives** are shortened from C stdint names:

| C Type     | Mangled |
| ---------- | ------- |
| `uint8_t`  | `u8`    |
| `int8_t`   | `i8`    |
| `uint16_t` | `u16`   |
| `int16_t`  | `i16`   |
| `uint32_t` | `u32`   |
| `int32_t`  | `i32`   |
| `uint64_t` | `u64`   |
| `int64_t`  | `i64`   |
| `bool`     | `bool`  |

**Tags** — the letter immediately following the separator identifies what
follows:

| Tag | Meaning            | Example  | Reads as    |
| --- | ------------------ | -------- | ----------- |
| `n` | VLA capacity       | `__n3`   | max 3 items |
| `d` | Fixed dimension(s) | `__d3x4` | `[3][4]`    |

Multiple fixed dimensions are joined with `x`: `__d3x4x9` means `[3][4][9]`.

**Type constructors** are prefixed words:

| Constructor | Prefix         | Separator | Meaning                       |
| ----------- | -------------- | --------- | ----------------------------- |
| VLA         | `vla__`        | `__`      | Variable length array struct  |
| Optional    | `optional__`   | `__`      | Presence-flagged wrapper      |
| Union       | `union{N}__`   | `__`      | Tagged union (N = variant count) |

### Grammar

Names read left-to-right as a prefix-notation type expression. `__` is the
uniform structural boundary:

```
<mangled>    ::= <outer>* <inner>
<outer>      ::= "vla__" <inner> "__n" <number>
               | "optional__" <inner>
               | "union" <count> "__" <inner> ("__" <inner>)*
<inner>      ::= <base> ("__" <modifier>)*
<base>       ::= <primitive> | <struct-name>
<modifier>   ::= "n" <number>                    -- VLA capacity
               | "d" <number> ("x" <number>)*     -- fixed dimensions
<count>      ::= <number>                         -- variant count
```

### Examples

| Type Expression                 | Mangled Name                          |
| ------------------------------- | ------------------------------------- |
| `VLA<u32, 3>`                   | `vla__u32__n3`                        |
| `VLA<VLA<u32, 3>, 4>`           | `vla__vla__u32__n3__n4`               |
| `VLA<VLA<VLA<u32, 3>, 4>, 5>`   | `vla__vla__vla__u32__n3__n4__n5`      |
| `VLA<u32[3], 4>`                | `vla__u32__d3__n4`                    |
| `VLA<u32[4][3], 5>`             | `vla__u32__d4x3__n5`                  |
| `Optional<u32>`                 | `optional__u32`                       |
| `Optional<u8[32]>`              | `optional__u8__d32`                   |
| `Optional<u8[3][4][9]>`         | `optional__u8__d3x4x9`               |
| `Optional<thing_nested>`        | `optional__thing_nested`              |
| `Optional<VLA<u32, 3>>`         | `optional__vla__u32__n3`              |
| `Optional<VLA<VLA<u32, 3>, 4>>` | `optional__vla__vla__u32__n3__n4`     |

### C Output

Each VLA produces a struct with `len`, `_pad`, and `items`. The `_pad` field
aligns `items` to an 8-byte boundary so that `offsetof(items)` is consistent
across architectures where `uint64_t` items would otherwise shift alignment.
A future arch-aware codegen flag may elide `_pad` on targets where it is
unnecessary.

```c
struct vla__u32__n3 {
    uint32_t len;
    uint8_t _pad[4];
    uint32_t items[3];
};
```

Each optional produces a union wrapper and an `optional` struct. The union is
named using the general `union{N}__` convention (where N is the variant count),
which extends naturally to multi-variant unions for future `oneOf`/`anyOf`
support:

```c
union union1__u32 {
    uint32_t value;
};

struct optional__u32 {
    bool present;
    union union1__u32 maybe;
};
```

### Deduplication

Wrapper types are shared. If two struct fields are both `Optional<u32>`, the
`optional__u32` struct is emitted once. Identity is determined by structural
equality on the type representation in the IR, not by string comparison of the
mangled name. The name is an output of the identity, not the identity itself.

### Prefix Interaction

User-configured prefixes (e.g., `fooey`) apply to user-defined struct names and
their encode/decode functions, but **not** to generated wrapper types.
`optional__u32` stays `optional__u32` regardless of prefix. Wrapper types are
library-level primitives shared across all prefixed namespaces.

## Generated C API

### Semantics

- **`decode`** — copies data into caller's struct (owned)
- **`parse`** — references data in the source JSON buffer (zero-copy)

### Token Count

Every generated type has a deterministic max token count, computed at codegen
time from the IR:

| IR Type                      | Max Tokens                      |
| ---------------------------- | ------------------------------- |
| `bool`, `number`, `null`     | 1                               |
| `string`                     | 1                               |
| `object` with fields f1..fn  | 1 + n + sum(ntoks(fi))          |
| `array` of T, maxItems N     | 1 + N * ntoks(T)                |
| `ref` to descriptor D        | ntoks(D)                        |

Optional fields are counted (worst case: all present).

### Types

```c
struct thing {
    uint8_t name[32];
    int32_t age;
};

struct thing_ref {
    const char *name;
    uint32_t name_len;
    int32_t age;
};
```

The `_ref` variant is only generated when the type contains string fields
(recursively through refs). Primitive-only types have no `_ref` variant.

### Functions

```c
#define THING_JSMN_NTOKS 7

/* Owned — caller-managed tokens (core implementation) */
int32_t decode_thing_tok(struct thing *dst, const char *src, uint32_t slen,
                         jsmntok_t *toks, uint32_t ntoks);

/* Owned — convenience wrapper (static inline, stack-local tokens) */
static inline int32_t
decode_thing(struct thing *dst, const char *src, uint32_t slen);

/* Ref — caller-managed tokens */
int32_t parse_thing_tok(struct thing_ref *dst, const char *src, uint32_t slen,
                        jsmntok_t *toks, uint32_t ntoks);

/* Ref — convenience wrapper */
static inline int32_t
parse_thing(struct thing_ref *dst, const char *src, uint32_t slen);

/* Encode (owned type only) */
int32_t encode_thing(uint8_t *dst, uint32_t dlen, const struct thing *src);
uint32_t len_thing(const struct thing *val);
```

The `_tok` variants are the core implementations. The convenience wrappers
declare `jsmntok_t toks[THING_JSMN_NTOKS]` on the stack and forward.

## Test Strategy

Test fixtures copied from schema_tools cover:

- All primitive types (bool, integers, strings, null)
- Fixed and variable length arrays
- Nested objects and arrays of objects
- Optional fields
- Multi-dimensional arrays
- Dependency ordering edge cases

Each fixture is a `.yml` schema paired with expected `.h` output.
