"""CLI entry point for schema tools cli"""

import argparse
import shutil
import sys
from importlib.resources import files
from pathlib import Path

JSMN_RUNTIME_DIR = files("jsmn_forge").joinpath("lang", "jsmn", "runtime")


def _cmake_dir() -> str:
    pkg = files("jsmn_forge").joinpath("cmake")
    if Path(str(pkg)).is_dir():
        return str(pkg)
    # Editable install: cmake/ lives at repo root, not inside the package.
    repo = Path(__file__).resolve().parents[3]
    fallback = repo / "cmake" / "modules"
    if fallback.is_dir():
        return str(fallback)
    raise FileNotFoundError("Cannot locate schema tools cmake modules")


def _generate(_args: argparse.Namespace) -> None:
    raise NotImplementedError()


def _runtime(args: argparse.Namespace) -> None:
    dest = Path(args.output).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("runtime.c", "runtime.h", "jsmn.h"):
        fin = JSMN_RUNTIME_DIR / name
        fout = dest / name
        shutil.copy2(str(fin), str(fout))


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
    gen_parser = subparsers.add_parser("generate", help="code generator")
    gen_parser.add_argument("specs", nargs="+", help="YAML spec files")
    gen_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output directory",
    )

    # Runtime only
    rt_parser = subparsers.add_parser("runtime", help="Emit runtime only")
    rt_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output directory",
    )

    parser.add_argument(
        "--runtime",
        choices=["bundled", "external"],
        default="bundled",
        help="Runtime bundling mode (default: bundled)",
    )

    args = parser.parse_args()
    if args.cmake_dir:
        print(_cmake_dir())
    elif args.command == "generate":
        _generate(args)
    elif args.command == "runtime":
        _runtime(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
