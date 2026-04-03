"""CLI entry point for jsmn tools cli"""

import argparse
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

from jinja2 import Environment as JinjaEnvironment
from referencing import Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from jsmn_tools.jsmn import Environment

JSMN_RUNTIME_DIR = files("jsmn_tools").joinpath("jsmn", "runtime")
RUNTIME_FILES = ("runtime.c", "runtime.h", "jsmn.h")

yaml = YAML(typ="safe")


def parse_spec(p: str) -> Resource:
    y = yaml.load(Path(p))
    return Resource.from_contents(y, default_specification=DRAFT202012)


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


def _render(args: argparse.Namespace) -> None:
    resources = [parse_spec(s) for s in args.specs]
    extra_env = dict(e.split("=", 1) for e in args.env)
    jsmn = Environment.from_specifications(*resources)
    env = JinjaEnvironment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    jsmn.extend(env, prefix=args.prefix or "jsmn_")
    if extra_env:
        env.globals.update(extra_env)
    for src, out in args.templates:
        tpl = Path(src).read_text(encoding="utf-8")
        Path(out).write_text(env.from_string(tpl).render(), encoding="utf-8")


def _generate_zephyr(args: argparse.Namespace) -> None:
    # Lazy import: west is an optional dependency (pip install jsmn-tools[zephyr])
    from jsmn_tools.plugin.zephyr import (
        collect,
        parse_autoconfig,
        parse_workspace,
        render,
    )

    config = parse_autoconfig(args.build_dir)
    workspace = parse_workspace()
    result = collect(workspace, config)
    errors = render(result, prefix=args.prefix or "jsmn_")
    for e in result.errors + errors:
        print(f"warning: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jsmn-tools", description="jsmn tools"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Top level commands
    parser.add_argument(
        "--cmake-dir",
        action="store_true",
        help="Print cmake module install path",
    )

    # Render sub command (low-level: explicit specs + templates)
    render_parser = subparsers.add_parser("render", help="render templates")
    render_parser.add_argument("specs", nargs="*", help="YAML spec files")
    render_parser.add_argument(
        "--template",
        nargs=2,
        action="append",
        metavar=("TEMPLATE", "OUTPUT"),
        dest="templates",
        default=[],
        help="Template and output filename pair",
    )
    render_parser.add_argument(
        "--env",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        help="User-defined template variable",
    )
    render_parser.add_argument(
        "--prefix",
        help="Function/type prefix (default: jsmn_)",
    )

    # Generate sub command (workspace-driven codegen)
    gen_parser = subparsers.add_parser("generate", help="workspace codegen")
    gen_subparsers = gen_parser.add_subparsers(dest="generator")

    zephyr_parser = gen_subparsers.add_parser(
        "zephyr", help="generate from zephyr workspace"
    )
    zephyr_parser.add_argument(
        "--build-dir",
        required=True,
        help="Zephyr build directory (CMAKE_BINARY_DIR)",
    )
    zephyr_parser.add_argument(
        "--prefix",
        help="Function/type prefix (default: jsmn_)",
    )

    args = parser.parse_args()
    if args.cmake_dir:
        print(_cmake_dir())
    elif args.command == "render":
        _render(args)
    elif args.command == "generate" and args.generator == "zephyr":
        _generate_zephyr(args)
    else:
        parser.print_help()
        _die("no command specified")


if __name__ == "__main__":
    main()
