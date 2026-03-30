"""CLI entry point for schema tools cli"""

import argparse
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from schema_tools.lang.jsmn.flatten import flatten_with_resolver
from schema_tools.lang.jsmn.render import Renderer

JSMN_RUNTIME_DIR = files("schema_tools").joinpath("lang", "jsmn", "runtime")
RUNTIME_FILES = ("runtime.c", "runtime.h", "jsmn.h")

yaml = YAML(typ="safe")


def parse_spec(p: str) -> Resource:
    y = yaml.load(Path(p))
    return Resource.from_contents(y, default_specification=DRAFT202012)


def _die(fmt: str, *args: object) -> None:
    print(f"error: {fmt % args}" if args else f"error: {fmt}", file=sys.stderr)
    sys.exit(1)


def _cmake_dir() -> str:
    pkg = files("schema_tools").joinpath("cmake")
    if Path(str(pkg)).is_dir():
        return str(pkg)
    # Editable install: cmake/ lives at repo root, not inside the package.
    repo = Path(__file__).resolve().parents[3]
    fallback = repo / "cmake" / "modules"
    if fallback.is_dir():
        return str(fallback)
    raise FileNotFoundError("Cannot locate schema tools cmake modules")


def _generate(args: argparse.Namespace) -> None:
    resources = [parse_spec(s) for s in args.specs]
    extra_env = dict(e.split("=", 1) for e in args.env)
    registry: Registry[Any] = resources @ Registry()
    specs = [r.contents for r in registry.values()]
    compiled = flatten_with_resolver(*specs, resolver=registry.resolver())
    renderer = Renderer(compiled.decls, extra_env=extra_env)
    for src, out in args.templates:
        tpl = Path(src).read_text()
        Path(out).write_text(renderer.render(tpl))


def main() -> None:
    parser = argparse.ArgumentParser(prog="schema", description="schema tools")
    subparsers = parser.add_subparsers(dest="command")

    # Top level commands
    parser.add_argument(
        "--cmake-dir",
        action="store_true",
        help="Print cmake module install path",
    )

    # Code generator sub command
    gen_parser = subparsers.add_parser("generate", help="template renderer")
    gen_parser.add_argument("specs", nargs="*", help="YAML spec files")
    gen_parser.add_argument(
        "--template",
        nargs=2,
        action="append",
        metavar=("TEMPLATE", "OUTPUT"),
        dest="templates",
        default=[],
        help="Template and output filename pair",
    )
    gen_parser.add_argument(
        "--env",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        help="User-defined template variable",
    )
    gen_parser.add_argument(
        "--prefix",
        help="Function/type prefix (default: schema_)",
    )

    args = parser.parse_args()
    if args.cmake_dir:
        print(_cmake_dir())
    elif args.command == "generate":
        _generate(args)
    else:
        parser.print_help()
        _die("no command specified")


if __name__ == "__main__":
    main()
