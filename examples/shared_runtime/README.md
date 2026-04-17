# shared_runtime

Render the jsmn-tools runtime into its own library, then render each
component's descriptor tables + typed shims into its own library that links
against that single shared runtime. Two schemas here — `sensor_reading`
(component-a) and `device_heartbeat` (component-b) — both resolve back to
one copy of the polymorphic core at link time.

Contrast with `examples/amalgamate`, which concatenates everything into one
translation unit. This example splits the pieces across several libraries
so consumers can ship (and version) the runtime independently of each
component.

## What's here

- `component-a.yaml`, `component-b.yaml` — two OpenAPI specs, each
  declaring a single `x-jsmn-type`.
- `runtime.h.jinja`, `runtime.c.jinja` — templates that render
  `runtime.h` / `runtime.c`. No specs consumed; the payload is the same
  polymorphic core regardless of what types exist elsewhere.
- `component-a.h.jinja` / `component-a.c.jinja` (and `-b` counterparts) —
  templates that render descriptor tables and typed shims for that
  component's schema only.
- `main.c` — decodes one payload through each component.
- `CMakeLists.txt` — three `jsmn_render` calls produce three libraries
  (`runtime`, `component-a`, `component-b`); the components `target_link`
  against the shared runtime. Each component render passes a unique
  `PREFIX` (`comp_a_`, `comp_b_`) so its generated symbols — struct
  names, typed shims, and the baked-in `jsmn_{en,de}code` dispatcher —
  don't collide with the other component at link time.

## Prerequisites

- `jsmn` on `PATH`.
- CMake 3.20+ and a C compiler.

## Build and run

```console
$ cmake -B build -S .
$ cmake --build build
$ ./build/main
sensor:    id=7 celsius=18.2 humidity_pct=43 label=inlet
heartbeat: device_id=42 uptime_s=3600 online=true
```

## How it works

Each `.jinja` is a thin wrapper that `{% include %}`s a jsmn-tools payload
(`jsmn.h`, `runtime.h`, `runtime.c`, `jsmn_generated.h`, or
`jsmn_generated.c`) into place. Before the runtime payloads are loaded
into the Jinja environment, `prepare.py:read_and_strip()` removes every
`#include "..."` directive from them — so when you paste `jsmn.h` content
into `runtime.h.jinja`, the `#include "jsmn.h"` baked into `runtime.h`'s
source is already gone. The C compiler never looks for a `jsmn.h` file on
disk.

The runtime concentrates all jsmn parser implementations into one
translation unit (`runtime.c`): the template inlines `jsmn.h` with no
`JSMN_HEADER` define, emitting decls *and* impls. Components only see
jsmn *declarations* via `runtime.h` (which inlines `jsmn.h` with
`JSMN_HEADER` defined first, emitting decls only). That means component
`.c` files never compile duplicate copies of the parser. Components
also reference `jt_encode` / `jt_decode` / `jt_pack` / `jt_unpack` — the
polymorphic core defined in the runtime library — resolved at link time
against `libruntime`.

Each component defines its own thin dispatcher (`comp_a_encode`,
`comp_a_decode`, etc.) that binds a component-local descriptor-table
struct (`comp_a_schemas`) into the runtime's `jt_*` core. That's why
`PREFIX` is mandatory: without unique prefixes, both components would
define a symbol named `jsmn_encode`, collision. `--prefix` also
namespaces struct names and typed shims, so `main.c` sees distinct
`struct comp_a_sensor_reading` and `struct comp_b_device_heartbeat`
types.

`JT_HAS_FLOAT` is declared `PUBLIC` on the `runtime` target so that
components and the executable inherit it automatically. This keeps the
runtime's float-parsing code and each component's float struct fields in
sync.
