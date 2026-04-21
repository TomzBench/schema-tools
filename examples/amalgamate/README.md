# amalgamate

Render the jsmn parser, the jsmn-tools runtime, the generated codec, and the
application's `main()` into a single `.c` file — one translation unit, no
headers to ship, no library to link.

## What's here

- `sensor.yaml` — the same `sensor_reading` schema used by the other
  examples.
- `main.c.jinja` — a Jinja template that `{% include %}`s the jsmn source,
  runtime, and generated codec, followed by a `main()` that round-trips a
  JSON payload.
- `Makefile` — runs `jsmn render` to produce `build/main.c`, then compiles it.

## Prerequisites

- `jsmn` on `PATH`.
- GNU make and a C compiler.

## Build and run

```console
$ make run
jsmn render sensor.yaml --template main.c.jinja build/main.c
cc -Os -DJT_HAS_FLOAT -Wall -o build/main build/main.c
./build/main
decoded: id=7 celsius=18.2 humidity_pct=43 label=inlet
encoded: {"id":42,"celsius":23.5,"humidity_pct":61,"label":"ambient"}
```

`make clean` removes `build/`.

## How it works

`jsmn render` evaluates `main.c.jinja` in a Jinja environment that jsmn-tools
pre-loads with the runtime sources (`jsmn.h`, `runtime.h`, `runtime.c`) and
the generated codec (`jsmn_generated.h`, `jsmn_generated.c`). The template
pulls each in with `{% include %}`, concatenating everything into a single
translation unit.

This is the same pipeline `jsmn generate` uses under the hood — the
difference is that `generate` splits output across three files (for ordinary
project integration), while this template collapses them into one.
