# cmake

The same sensor round-trip as `examples/simple`, wired into CMake via
`find_package(JsmnTools)`. Re-runs codegen automatically whenever
`sensor.yaml` changes.

## What's here

- `sensor.yaml` — OpenAPI 3.1 spec declaring `sensor_reading`.
- `main.c` — decodes a JSON literal, then encodes a struct.
- `CMakeLists.txt` — locates the jsmn CMake modules, calls `jsmn_generate`
  to produce the codec sources, and links them into `main`.

## Prerequisites

- `jsmn` on `PATH`.
- CMake 3.20+ and a C compiler.

## Build and run

```console
$ cmake -B build -S .
$ cmake --build build
$ ./build/main
decoded: id=7 celsius=18.2 humidity_pct=43 label=inlet
encoded: {"id":42,"celsius":23.5,"humidity_pct":61,"label":"ambient"}
```

## How it works

The configure step shells out to `jsmn cmake-dir` to discover the path to
`JsmnToolsConfig.cmake`, then `find_package(JsmnTools)` loads the helpers.

`jsmn_generate` writes `jsmn.h`, `sensor.h`, and `sensor.c` into
`${CMAKE_CURRENT_BINARY_DIR}` and registers a custom target (`sensor_codegen`)
that depends on those outputs. It does **not** produce a library — the
generated `sensor.c` is compiled directly into `main`. Consumers are free to
wrap it in `add_library(... STATIC)` instead if that fits their project
better.

`-DJT_HAS_FLOAT` is set via `target_compile_definitions` because `celsius`
is a `float`.
