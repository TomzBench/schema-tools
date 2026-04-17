## Plugin

A Jsmn Tools Plugin is a Python module loaded via `jsmn render --plugin PATH`
(or `--plugin DIR` where `DIR` contains a `.jsmn-tools.py`). It extends the
renderer past what command-line arguments can express: programmatic spec
discovery, custom Jinja filters and globals, and a `jsmn bundle` entry
point. The CLI calls up to three top-level hooks, each at a specific
point in the render pipeline.

### collect(env)

Jsmn Tools leverages the
[`referencing`](https://referencing.readthedocs.io/en/stable/) library
for intra-doc `$ref` resolution, and exposes this interface directly
to the plugin layer. Plugin authors contribute to the specification
[`Registry`](https://referencing.readthedocs.io/en/stable/api/#referencing.Registry)
via the `collect` hook by returning a list of
[`Resource`](https://referencing.readthedocs.io/en/stable/api/#referencing.Resource)
objects. Anything returned here is **merged** with specs passed on the
command line, not replaced by them.

Typical uses:

- Glob a directory of specs
- Fetch specs from a URL or artifact registry
- Generate specs inline from code

```python
from pathlib import Path
from jsmn_tools.plugin.loader import load_resource

HERE = Path(__file__).parent

def collect(env):
    return [load_resource(p) for p in sorted((HERE / "specs").glob("*.yaml"))]
```

### bundle(env)

Called by `jsmn bundle` to produce a single merged spec on disk. Most
plugins already implement `collect`, so `bundle` is usually a one-line
wrapper around `load_bundle()` of the collected resources:

```python
from jsmn_tools.plugin.loader import load_bundle

def bundle(env):
    return load_bundle(*[r.contents for r in collect(env)])
```

### jinja(env)

The (optional) `jinja` hook lets plugin authors extend the Jinja
`Environment` with custom filters, tests, and globals — so templates
have the full capabilities expected of a normal Jinja environment.

```python
from jinja2 import Environment

def jinja(env):
    e = Environment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    e.filters["banner"] = lambda s: f"<!-- {'=' * 8} {s} {'=' * 8} -->"
    e.tests["is_public_api"] = lambda d: d.ctype.name.startswith("pub_")
    e.globals["project_name"] = env.get("project_name", "untitled")
    return e
```

### Plugin Configuration

The `env` dict passed to each hook is assembled from `--env KEY=VALUE`
CLI flags. It's the escape hatch for parameterizing a plugin at
invocation time — file paths, feature toggles, build metadata — without
changing the plugin source.

```console
$ jsmn render --plugin . --env project_name=sensor-kit --env build=release ...
```

### Zephyr integration

Jsmn Tools provides helpful methods under `jsmn_tools.plugin.zephyr`
for Zephyr workspaces. These extend the plugin `env` with selected
Kconfig parameters from the build's `autoconf.h`, and discover
schemas contributed by supporting
[west](https://docs.zephyrproject.org/latest/develop/west/index.html)
modules across the workspace. A plugin can then select schemas
programmatically based on build configuration, and reference schemas in a
multi-module project with a conventional syntax instead of hard coding paths.
