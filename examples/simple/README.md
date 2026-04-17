# simple

End-to-end walkthrough: an OpenAPI spec with one `x-jsmn-type` schema, the
generated codec, and a tiny `main.c` that round-trips a JSON payload through
it.

## What's here

- `sensor.yaml` — OpenAPI 3.1 spec declaring `sensor_reading` with four
  required fields (`id`, `celsius`, `humidity_pct`, `label`).
- `main.c` — decodes a JSON literal into `struct sensor_reading`, then encodes
  a struct back to JSON.

## Prerequisites

- `jsmn` on `PATH` (see the top-level README for install instructions).
- A C compiler.

## Build and run

Generate the codec, compile, and run:

```console
$ jsmn generate sensor.yaml --out-dir build/ --name sensor
$ cc -Os -DJT_HAS_FLOAT -Ibuild/ -o build/main main.c build/sensor.c
$ ./build/main
decoded: id=7 celsius=18.2 humidity_pct=43 label=inlet
encoded: {"id":42,"celsius":23.5,"humidity_pct":61,"label":"ambient"}
```

`jsmn generate` writes three files into `build/`: `jsmn.h`, `sensor.h`, and
`sensor.c`. Re-run it whenever `sensor.yaml` changes. Everything produced by
the build lives under `build/` so the source tree stays clean.

`-DJT_HAS_FLOAT` opts the runtime into float/double parsing — required here
because `celsius` is a `float`. Schemas that only use integers and strings
don't need it. (`-DJT_HAS_INT64` is the matching switch for 64-bit integers.)
