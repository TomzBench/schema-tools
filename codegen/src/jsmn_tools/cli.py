"""CLI entry point for jsmn tools cli

jsmn bundle [specs...] [--plugin PATH] [--env K=V...] --out-dir DIR
    - CLI specs: split by draft, join each, produce BundleResult
    - Plugin: plugin.bundle(env) -> BundleResult
    - Both: join per-draft across CLI and plugin results
    - Write up to 3 files to out-dir: openapi.yaml, asyncapi.yaml

jsmn render [specs...] [--plugin PATH] [--env K=V...] [--global K=V...]
            [--template SRC OUT...] [--prefix PREFIX]
    - CLI specs: load_resource(path) auto-assigns file:// $id -> Registry
    - Plugin: plugin.collect(env) -> Registry
    - Both: CLI resources @ plugin registry (combined)
    - Plugin jinja: plugin.jinja(env) -> Environment (optional)
    - bundle_codegen(registry) -> flatten + codegen pipeline -> render templates
"""

import argparse
import sys
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment
from referencing import Registry, Resource
from ruamel.yaml import YAML

from jsmn_tools.jsmn.prepare import bundle_codegen, extend_codegen
from jsmn_tools.plugin.loader import (
    BundleResult,
    Plugin,
    load_bundle,
    load_plugin,
    load_plugins,
    load_resource,
)
from jsmn_tools.spec import ASYNCAPI_3_0, OPENAPI_3_1
from jsmn_tools.walk import join

JSMN_RUNTIME_DIR = files("jsmn_tools").joinpath("jsmn", "runtime")
RUNTIME_FILES = ("runtime.c", "runtime.h", "jsmn.h")

yaml = YAML(typ="safe")


def _die(fmt: str, *args: object) -> None:
    print(f"error: {fmt % args}" if args else f"error: {fmt}", file=sys.stderr)
    sys.exit(1)


def _cmake_dir() -> str:
    pkg = files("jsmn_tools").joinpath("cmake")
    if Path(str(pkg)).is_dir():
        return str(pkg)
    # Editable install: cmake/ lives at repo root, not inside the package.
    repo = Path(__file__).resolve().parents[3]
    fallback = repo / "cmake" / "modules"
    if fallback.is_dir():
        return str(fallback)
    raise FileNotFoundError("Cannot locate jsmn tools cmake modules")


def _resolve_plugin(path: str) -> Plugin:
    p = Path(path)
    if p.is_file():
        return load_plugin(p)
    if p.is_dir():
        plugins = load_plugins([p])
        if not plugins:
            _die("no .jsmn-tools.py found in %s", path)
        return next(iter(plugins.values()))
    _die("plugin path does not exist: %s", path)


def _parse_kv(items: list[str]) -> dict[str, str]:
    return dict(e.split("=", 1) for e in items)


def _merge_bundles(a: BundleResult, b: BundleResult) -> BundleResult:
    oa = [x for x in [a.openapi, b.openapi] if x]
    aa = [x for x in [a.asyncapi, b.asyncapi] if x]
    return BundleResult(
        openapi=join(*oa, draft=OPENAPI_3_1).value if len(oa) > 1 else next(iter(oa), None),
        asyncapi=join(*aa, draft=ASYNCAPI_3_0).value if len(aa) > 1 else next(iter(aa), None),
        other=[*a.other, *b.other],
        conflicts=[*a.conflicts, *b.conflicts],
    )


# -- commands ----------------------------------------------------------------


def _cmd_cmake_dir(_args: argparse.Namespace) -> None:
    print(_cmake_dir())


def _cmd_bundle(args: argparse.Namespace) -> None:
    env = _parse_kv(args.env)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    cli_bundle = None
    plugin_bundle = None

    if args.specs:
        specs = [yaml.load(Path(s)) for s in args.specs]
        cli_bundle = load_bundle(*specs)

    if args.plugin:
        plugin = _resolve_plugin(args.plugin)
        plugin_bundle = plugin.bundle(env)

    if not cli_bundle and not plugin_bundle:
        _die("no specs provided (pass spec files or --plugin)")

    if cli_bundle and plugin_bundle:
        result = _merge_bundles(cli_bundle, plugin_bundle)
    else:
        result = cli_bundle or plugin_bundle

    for c in result.conflicts:
        print(f"warning: conflict at {c.location} from {c.id}", file=sys.stderr)

    writer = YAML()
    if result.openapi:
        writer.dump(result.openapi, out / "openapi.yaml")
    if result.asyncapi:
        writer.dump(result.asyncapi, out / "asyncapi.yaml")
    for i, other in enumerate(result.other):
        writer.dump(other, out / f"other.{i}.yaml")


def _cmd_render(args: argparse.Namespace) -> None:
    env = _parse_kv(args.env)
    plugin = _resolve_plugin(args.plugin) if args.plugin else None

    resources: list[Resource] = []
    if args.specs:
        resources += [load_resource(Path(s)) for s in args.specs]
    if plugin:
        resources += plugin.collect(env)
    if not resources:
        _die("no specs provided (pass spec files or --plugin)")
    registry = resources @ Registry()

    jinja_hook = getattr(plugin, "jinja", None) if plugin else None
    jinja_env = jinja_hook(env) if jinja_hook else None

    env_obj = jinja_env or Environment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    resolver, bundle = bundle_codegen(registry)
    extend_codegen(env_obj, bundle, resolver=resolver, prefix=args.prefix or "jsmn_")

    if args.globals:
        env_obj.globals.update(_parse_kv(args.globals))

    for src, dst in args.templates:
        tpl = Path(src).read_text(encoding="utf-8")
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        Path(dst).write_text(env_obj.from_string(tpl).render(), encoding="utf-8")


def _cmd_generate(_args: argparse.Namespace) -> None:
    _die("generate is not yet implemented")


# -- argparse ----------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jsmn-tools",
        description="jsmn tools",
    )
    subparsers = parser.add_subparsers()

    # cmake-dir
    p = subparsers.add_parser("cmake-dir", help="print cmake module path")
    p.set_defaults(func=_cmd_cmake_dir)

    # bundle
    p = subparsers.add_parser("bundle", help="join and bundle specs")
    p.add_argument("specs", nargs="*", help="YAML spec files")
    p.add_argument("--plugin", metavar="PATH", help="plugin file or directory")
    p.add_argument(
        "--env", action="append", metavar="KEY=VALUE", default=[],
        help="config passed to plugin",
    )
    p.add_argument("--out-dir", required=True, help="output directory")
    p.set_defaults(func=_cmd_bundle)

    # render
    p = subparsers.add_parser("render", help="render custom templates")
    p.add_argument("specs", nargs="*", help="YAML spec files")
    p.add_argument(
        "--template", nargs=2, action="append", metavar=("TEMPLATE", "OUTPUT"),
        dest="templates", default=[], help="template and output pair",
    )
    p.add_argument("--plugin", metavar="PATH", help="plugin file or directory")
    p.add_argument(
        "--env", action="append", metavar="KEY=VALUE", default=[],
        help="config passed to plugin",
    )
    p.add_argument(
        "--global", action="append", metavar="KEY=VALUE", default=[],
        dest="globals", help="template variable",
    )
    p.add_argument("--prefix", help="function/type prefix (default: jsmn_)")
    p.set_defaults(func=_cmd_render)

    # generate (stub)
    p = subparsers.add_parser("generate", help="generate code from specs")
    p.add_argument("specs", nargs="+", help="YAML spec files")
    p.add_argument("--out-dir", required=True, help="output directory")
    p.add_argument("--prefix", help="function/type prefix (default: jsmn_)")
    p.set_defaults(func=_cmd_generate)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
