# schema-tools vs schema_tools — Feature Gap Analysis

Comparison of schema-tools (successor) against the legacy schema_tools (Rust/CBOR)
to identify gaps before deprecation.

## Feature Matrix

| Feature                      | schema_tools (legacy)              | schema-tools (new)                  | Gap                             |
| ---------------------------- | ---------------------------------- | --------------------------------- | ------------------------------- |
| **Spec Formats**             |                                    |                                   |                                 |
| OpenAPI 3.0                  | Yes                                | —                                 | Not targeted (3.1 only)         |
| OpenAPI 3.1                  | —                                  | Yes                               | —                               |
| AsyncAPI                     | Partial (channels/messages)        | Partial (bundle infra only)       | Parity                          |
| JSON Schema Draft 2020-12    | —                                  | Yes (via referencing lib)         | —                               |
| **Wire Formats**             |                                    |                                   |                                 |
| JSON encode/decode           | Partial (serde-json-core)          | Full (jsmn + custom runtime)      | schema-tools ahead                |
| CBOR encode/decode           | Full (minicbor)                    | —                                 | **Gap: no CBOR**                |
| **Primitives**               |                                    |                                   |                                 |
| u8/i8/u16/i16/u32/i32        | Yes                                | Yes                               | Parity                          |
| u64/i64                      | Yes                                | Yes (compile flag)                | Parity                          |
| float/double                 | —                                  | Yes (compile flag)                | schema-tools ahead                |
| bool                         | Yes                                | Yes                               | Parity                          |
| string (fixed buffer)        | Yes                                | Yes                               | Parity                          |
| **Complex Types**            |                                    |                                   |                                 |
| Objects (structs)            | Yes                                | Yes                               | Parity                          |
| Nested objects               | Yes                                | Yes                               | Parity                          |
| Optional fields              | Yes (`optional__T` wrapper)        | Yes (`optional__T` wrapper)       | Parity                          |
| Arrays (fixed)               | Yes                                | Yes                               | Parity                          |
| Arrays (VLA)                 | Yes (`vla__T_N`)                   | Yes (`vla__T__nN`)                | Parity                          |
| Nested arrays (multi-dim)    | Yes                                | Yes (all 8 combos tested)         | Parity                          |
| Top-level arrays             | —                                  | Yes (new!)                        | schema-tools ahead                |
| **Composition**              |                                    |                                   |                                 |
| `$ref` (same file)           | Yes                                | Yes                               | Parity                          |
| `$ref` (cross file)          | Yes                                | Yes (URI scheme)                  | Parity                          |
| `x-extends` (inheritance)    | Yes                                | —                                 | **Gap: no inheritance**         |
| `allOf`                      | —                                  | Yes (flatten merges branches)     | Parity                          |
| `anyOf/oneOf`                | —                                  | `NotImplementedError`             | **Gap: composition**            |
| Enums (C enum codegen)       | —                                  | —                                 | Neither has it                  |
| Union/discriminated unions   | Partial (global vtable)            | Yes (descriptor table dispatch)   | Parity                          |
| **Annotations**              |                                    |                                   |                                 |
| `x-type-id` (name override)  | Yes                                | `x-st-generate` (equivalent)    | Parity (different name)         |
| `x-extends`                  | Yes                                | —                                 | **Gap**                         |
| **Validation**               |                                    |                                   |                                 |
| Number range (min/max)       | Yes (CBOR runtime)                 | Overflow/underflow only           | **Gap: no min/max constraints** |
| `multipleOf`                 | Yes                                | —                                 | **Gap**                         |
| String `minLength`           | Yes                                | — (only maxLength)                | **Gap**                         |
| String `pattern` (regex)     | Stub                               | —                                 | Neither complete                |
| **Runtime**                  |                                    |                                   |                                 |
| Implementation language      | Rust (no_std FFI)                  | C (pure, no dependencies)         | Architectural difference        |
| Zero-copy strings            | Yes                                | Yes (pointer into JSON src)       | Parity                          |
| Heap-free operation          | Yes                                | Yes                               | Parity                          |
| Error codes                  | 11 codes                           | 10 codes                          | Parity                          |
| Worst-case buffer sizing     | —                                  | Yes (compile-time `_LEN`)         | schema-tools ahead                |
| Descriptor tables            | —                                  | Yes (rt_struct/field/array)       | schema-tools ahead                |
| **Build Integration**        |                                    |                                   |                                 |
| CMake module                 | Yes (comprehensive)                | Yes (`schema_tools_generate`)     | Parity                          |
| Cargo/Rust build             | Yes (workspace)                    | — (Python only)                   | N/A (different arch)            |
| Zephyr/Kconfig               | Yes (deep integration)             | —                                 | **Gap: no Zephyr integration**  |
| Conditional resources (`if`) | Yes (Kconfig flags)                | Yes (workspace guards)            | Parity                          |
| **Code Output**              |                                    |                                   |                                 |
| C header generation          | Yes                                | Yes                               | Parity                          |
| C source generation          | —                                  | Yes (.c with tables + functions)  | schema-tools ahead                |
| Global vtable/dispatch       | Yes (anyOf enum + union)           | Yes (generic key/ptr dispatch)    | Parity                          |
| Prefix support               | Yes (`CONFIG_SCHEMA_TOOLS_PREFIX`) | Yes (`--prefix`)                  | Parity                          |
| Amalgamation                 | —                                  | TODO                              | Neither complete                |
| **Testing**                  |                                    |                                   |                                 |
| Unit tests                   | Yes                                | Yes                               | Parity                          |
| Snapshot tests               | Yes (trybuild)                     | Yes (syrupy)                      | Parity                          |
| E2E roundtrip tests          | —                                  | Yes (CMake + Unity)               | schema-tools ahead                |

## Key Gaps

### Must-have for deprecation

1. **`x-extends` (object inheritance)** — schema_tools uses this for property
   merging. Specs using it won't work without support. Standard replacement is
   `allOf`, so a normalize pass that rewrites `x-extends` → `allOf` would close
   this gap without touching flatten.
2. **`anyOf/oneOf` composition** — `allOf` is implemented (flatten merges
   branches into one struct). `anyOf`/`oneOf` still `NotImplementedError` — these
   need tagged union codegen.
3. ~~**Union/vtable dispatch**~~ — **Resolved.** The runtime descriptor tables
   expose a generic key/ptr dispatch API for polymorphic encode/decode, equivalent
   to schema_tools' global anyOf vtable.

### Nice-to-have

4. **CBOR support** — schema_tools' primary wire format. If downstream users
   only need JSON, not blocking.
5. **Number constraints** (`minimum`, `maximum`, `multipleOf`) — runtime
   validation, not structural.
6. **String `minLength`** — minor validation gap.
7. **Zephyr Kconfig integration** — platform-specific, can be added via CMake
   module.

### Not gaps (architectural differences)

- Rust runtime vs C runtime — intentional redesign, not a missing feature.
- OpenAPI 3.0 vs 3.1 — 3.1 is the successor, not a regression.
