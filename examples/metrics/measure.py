"""Measure generated code size vs. N x-jsmn-types.

Usage:
    python measure.py                   # sweep the default N values
    python measure.py 50                # build+size at a single N
    python measure.py 1 10 100          # sweep custom N values
    python measure.py --shared-names    # share field names across schemas
                                        # (lets the strings pool dedupe)
    python measure.py --calls 3         # 3 decode+encode pairs per type
                                        # in main() (default: 0)
    python measure.py --shim-mode none  # polymorphic API, no typed shims
    python measure.py --json out.json   # also write structured results
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment

HERE = Path(__file__).parent
BUILD = HERE / "build"

SWEEP = [1, 10, 50, 100, 500, 1000]
CC = os.environ.get("CC", "cc")
CFLAGS = ["-Os", "-DJT_HAS_FLOAT", "-Wall"]

_yaml_env = Environment(trim_blocks=True, lstrip_blocks=True)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    if r.returncode != 0:
        sys.stderr.write(f"command failed: {' '.join(cmd)}\n")
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        sys.exit(r.returncode)
    return r


def _parse_size(stdout: str) -> dict[str, int]:
    lines = stdout.splitlines()
    cols = lines[0].split()
    vals = lines[1].split()
    out = {}
    for k, v in zip(cols, vals):
        try:
            out[k] = int(v)
        except ValueError:
            pass  # hex/filename cols
    return out


def _measure_one(
    n: int, shared: bool, calls: int, shim_mode: str | None
) -> dict[str, int]:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir()

    spec_tpl = (HERE / "sensor.yaml.jinja").read_text(encoding="utf-8")
    (BUILD / "sensor.yaml").write_text(
        _yaml_env.from_string(spec_tpl).render(n=n, shared=shared),
        encoding="utf-8",
    )

    cmd = [
        "jsmn",
        "render",
        "build/sensor.yaml",
        "--global",
        f"calls={calls}",
        "--template",
        "main.c.jinja",
        "build/main.c",
    ]
    if shim_mode:
        cmd += ["--shim-mode", shim_mode]
    _run(cmd)
    _run([CC, *CFLAGS, "-c", "-o", "build/main.o", "build/main.c"])
    return _parse_size(_run(["size", "build/main.o"]).stdout)


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "n",
        nargs="*",
        type=int,
        help="N values to build (default: %(default)s)",
        default=SWEEP,
    )
    p.add_argument(
        "--shared-names",
        action="store_true",
        help="share field names across all schemas (best-case dedup)",
    )
    p.add_argument(
        "--calls",
        type=int,
        default=0,
        metavar="C",
        help="decode+encode call-site pairs per type in main() (default: 0)",
    )
    p.add_argument(
        "--shim-mode",
        choices=["extern", "inline", "none"],
        default=None,
        help="typed-shim emission mode (default: extern)",
    )
    p.add_argument(
        "--json",
        metavar="PATH",
        help="also write results as a JSON array to PATH",
    )
    args = p.parse_args()

    records: list[dict[str, object]] = []
    header_printed = False
    for n in args.n:
        sizes = _measure_one(
            n,
            shared=args.shared_names,
            calls=args.calls,
            shim_mode=args.shim_mode,
        )
        records.append(
            {
                "n": n,
                "calls": args.calls,
                "shared": args.shared_names,
                "shim_mode": args.shim_mode or "extern",
                **sizes,
            }
        )
        if not header_printed:
            cols = " ".join(f"{k:>8}" for k in sizes)
            print(f"   N   {cols}")
            header_printed = True
        vals = " ".join(f"{v:>8}" for v in sizes.values())
        print(f"{n:4d}   {vals}")

    if args.json:
        Path(args.json).write_text(json.dumps(records, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
