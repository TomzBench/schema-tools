"""Minimal jsmn-tools plugin.

Exposes three hooks the CLI will call:

- collect(env)  — programmatic spec discovery. Anything returned here is
  merged with specs passed on the command line.
- bundle(env)   — `jsmn bundle` entry point; joins the collected specs.
- jinja(env)    — pre-populates a Jinja Environment with extra filters,
  tests, or globals before jsmn-tools overlays its own codegen bits.

The `env` dict is populated from `--env KEY=VALUE` CLI flags.
"""

from pathlib import Path

from jinja2 import Environment

from jsmn_tools.plugin.loader import load_bundle, load_resource

HERE = Path(__file__).parent


def collect(env):
    return [load_resource(p) for p in sorted((HERE / "specs").glob("*.yaml"))]


def bundle(env):
    return load_bundle(*[r.contents for r in collect(env)])


def jinja(env):
    e = Environment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    e.filters["banner"] = lambda s: (
        f"<!-- {'=' * 8} {s} {'=' * 8} -->"
    )
    e.globals["project_name"] = env.get("project_name", "untitled")
    return e
