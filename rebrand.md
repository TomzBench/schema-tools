# Rebrand: jsmn-forge → schema-tools

Rename the project to `schema_tools` (Python) / `schema-tools` (package/CLI).
Major version bump (1.0.0) signals the break from legacy schema_tools (Rust).

## Do NOT rename

- `jsmn.h` / `jsmn` library references — upstream parser dependency
- `SchemaToolsConfig.cmake` / `schema_tools_generate()` — already correct

## Rename inventory

### 1. Python package directory

| From                      | To                          |
| ------------------------- | --------------------------- |
| `codegen/src/jsmn_forge/` | `codegen/src/schema_tools/` |

All internal imports follow (19 modules across node/, spec/, walk/, lang/jsmn/).

### 2. pyproject.toml

| Line | From                                         | To                                               |
| ---- | -------------------------------------------- | ------------------------------------------------ |
| 2    | `name = "jsmn-forge"`                        | `name = "schema-tools"`                          |
| 14   | `jsmn-forge-codegen = "jsmn_forge.cli:main"` | `schema-tools-codegen = "schema_tools.cli:main"` |
| 41   | `packages = ["codegen/src/jsmn_forge"]`      | `packages = ["codegen/src/schema_tools"]`        |
| 47   | `"cmake/modules" = "jsmn_forge/cmake"`       | `"cmake/modules" = "schema_tools/cmake"`         |

### 3. Config file pattern

| File                 | From                                               | To                                                       |
| -------------------- | -------------------------------------------------- | -------------------------------------------------------- |
| `bundle.py:16`       | `r"^\.?(jsmnForge\|JsmnForge\|jsmn-forge).ya?ml$"` | `r"^\.?(schemaTools\|SchemaTools\|schema-tools).ya?ml$"` |
| 3 workspace fixtures | `.jsmn-forge.yaml`                                 | `.schema-tools.yaml`                                     |

### 4. OpenAPI extension

| From              | To               |
| ----------------- | ---------------- |
| `x-jsmn-forge-as` | `x-st-generate` |

~33 occurrences across: flatten.py (4), 10+ YAML fixtures, README, design doc.

### 5. C runtime symbols

The active C runtime lives in `codegen/src/jsmn_forge/lang/jsmn/runtime/`
(moves with the Python package rename). No file renames needed — `runtime.c`,
`runtime.h`, and `jsmn.h` keep their names.

**Symbol renames (`JF_` → `ST_`, `jf_` → `st_`):**

All C API symbols rebrand from the `jf`/`JF` prefix (derived from "jsmn-forge")
to `st`/`ST` (derived from "schema-tools").

- **Error codes (5):** `JF_OK`, `JF_ERR_PARSE`, `JF_ERR_TYPE`,
  `JF_ERR_REQUIRED`, `JF_ERR_OVERFLOW`, `JF_ERR_BUFFER` → `ST_OK`,
  `ST_ERR_PARSE`, etc.
- **Type enum:** `enum jf_type` → `enum st_type`; `JF_BOOL`, `JF_U8`, ...,
  `JF_OBJECT` → `ST_BOOL`, `ST_U8`, ..., `ST_OBJECT`
- **Field flags (3):** `JF_F_OPTIONAL`, `JF_F_ARRAY`, `JF_F_VLA` → `ST_F_*`
- **Structs:** `struct jf_struct`, `struct jf_field` → `struct st_struct`,
  `struct st_field`
- **Functions (5):** `jf_decode`, `jf_decode_object`, `jf_encode`, `jf_len`,
  `jf_tok_skip` → `st_decode`, `st_decode_object`, `st_encode`, `st_len`,
  `st_tok_skip`
- **Internal types:** `jf_acc_t`, `jf_sacc_t` → `st_acc_t`, `st_sacc_t`
- **Compile flags:** `JF_HAS_FLOAT`, `JF_HAS_INT64`, `JF_ACC_MAX` →
  `ST_HAS_FLOAT`, `ST_HAS_INT64`, `ST_ACC_MAX`

**Files affected:**

| File | `jf_`/`JF_` count |
|------|--------------------|
| `codegen/src/.../runtime/runtime.c` | ~37 |
| `codegen/tests/integration/__snapshots__/test_jsmn_render.ambr` | ~37 |
| `codegen/tests/e2e/test_tok.c`, `test_tok_ex.c`, `test_fmt.c` | ~20 total |

### 6. CMake

| File                                    | From                                   | To                                       |
| --------------------------------------- | -------------------------------------- | ---------------------------------------- |
| `codegen/tests/e2e/CMakeLists.txt`      | `project(jsmn-forge-e2e)`              | `project(schema-tools-e2e)`              |
|                                         | `python -m jsmn_forge.cli`             | `python -m schema_tools.cli`             |
| `cmake/modules/SchemaToolsConfig.cmake` | `find_program(... jsmn-forge-codegen)` | `find_program(... schema-tools-codegen)` |

### 7. Render defaults

| File            | From                               | To                                   |
| --------------- | ---------------------------------- | ------------------------------------ |
| `render.py:250` | `PackageLoader("jsmn_forge", ...)` | `PackageLoader("schema_tools", ...)` |

### 8. Tooling config

| File                 | From                                  | To                                      |
| -------------------- | ------------------------------------- | --------------------------------------- |
| `ruff.toml:27`       | `known-first-party = ["jsmn-forge"]`  | `known-first-party = ["schema-tools"]`  |
| `.importlinter:2`    | `root_package = jsmn_forge`           | `root_package = schema_tools`           |
| `.importlinter:8-10` | `jsmn_forge.spec` / `.walk` / `.node` | `schema_tools.spec` / `.walk` / `.node` |
| `package.json:2`     | `"name": "jsmn-forge"`                | `"name": "schema-tools"`                |
| `package.json:15`    | `"jsmn-forge": "./dist/cli.js"`       | `"schema-tools": "./dist/cli.js"`       |

### 9. Documentation

| File                                       | Change                                      |
| ------------------------------------------ | ------------------------------------------- |
| `CLAUDE.md`                                | Title, description, directory paths         |
| `docs/index.md`                            | Title                                       |
| `docs/conf.py`                             | `project = "schema-tools"`                  |
| `codegen/tests/fixtures/flatten/README.md` | Extension name references                   |
| `schema-tools-compare.md`                  | Extension name references                   |
| `docs/ai/local/design.md`                  | All jsmn-forge / x-jsmn-forge-as references |

### 10. Snapshot tests

`codegen/tests/integration/__snapshots__/test_jsmn_render.ambr` — no jsmn_forge
references currently, but the test file is named `test_jsmn_render.py`. Rename
is optional since "jsmn" here refers to the C backend, not the project.

## Execution order

1. Rename Python package directory
2. Find-and-replace all imports (`jsmn_forge` → `schema_tools`)
3. Rename C runtime symbols (`JF_`/`jf_` → `ST_`/`st_`)
4. Update CMake targets
5. Update config files (pyproject, ruff, importlinter, package.json)
6. Update bundle.py regex and config file fixtures
7. Update `x-jsmn-forge-as` → `x-schema-tools-as` in code + all fixtures
8. Update render.py PackageLoader
9. Update cli.py package refs (`files("jsmn_forge")` → `files("schema_tools")`)
10. Update documentation
11. Update cmake module executable name
12. Update snapshot tests (regenerate after symbol renames)
13. `uv lock` to regenerate lockfile
14. Run full test suite
