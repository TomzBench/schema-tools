"""Sweep modes x N x C and render two SVG charts for docs.

Chart 1: size vs N (types), at C=1, one line per shim mode.
Chart 2: size vs C (decode+encode pairs per type), at N=100, one line per mode.

    python plot.py                     # run sweeps, write SVGs next to this file
    python plot.py --out-dir docs/_static

Output:
    <out-dir>/metrics_n.svg
    <out-dir>/metrics_c.svg
    <out-dir>/metrics_data.json       (raw sweep data for reproducibility)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt

# Keep tick labels as text (not vectorized paths) so SVG diffs + greps work.
plt.rcParams["svg.fonttype"] = "none"

HERE = Path(__file__).parent

MODES = ["extern", "inline", "none"]
N_SWEEP = [1, 10, 50, 100, 200, 500]
N_CHART_CALLS = 1  # each type exercised once — realistic low-use floor
C_SWEEP = [0, 1, 3, 5, 10]
C_CHART_N = 100

# Match the Furo/Altronix palette (see docs/conf.py).
COLORS = {
    "extern": "#0072CE",
    "inline": "#E89F00",
    "none": "#2CA02C",
}

# Distinct linestyle per mode so overlapping lines stay visible (e.g. inline
# and none coincide on the N chart at C=1).
LINESTYLES = {
    "extern": "-",
    "inline": "--",
    "none": ":",
}


def _run_measure(
    n_values: list[int], calls: int, mode: str
) -> list[dict[str, object]]:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False
    ) as tmp:
        json_path = tmp.name
    try:
        subprocess.run(
            [
                sys.executable,
                str(HERE / "measure.py"),
                *[str(n) for n in n_values],
                "--calls",
                str(calls),
                "--shim-mode",
                mode,
                "--json",
                json_path,
            ],
            check=True,
        )
        return json.loads(Path(json_path).read_text())
    finally:
        Path(json_path).unlink(missing_ok=True)


def _sweep() -> dict[str, list[dict[str, object]]]:
    """Collect size-vs-N (at C=N_CHART_CALLS) and size-vs-C (at N=C_CHART_N)."""
    data: dict[str, list[dict[str, object]]] = {"by_n": [], "by_c": []}
    for mode in MODES:
        print(f"[by_n] mode={mode} calls={N_CHART_CALLS}", flush=True)
        data["by_n"].extend(
            _run_measure(N_SWEEP, calls=N_CHART_CALLS, mode=mode)
        )
    for mode in MODES:
        for c in C_SWEEP:
            print(f"[by_c] mode={mode} calls={c} n={C_CHART_N}", flush=True)
            data["by_c"].extend(_run_measure([C_CHART_N], calls=c, mode=mode))
    return data


def _plot_by_n(records: list[dict[str, object]], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for mode in MODES:
        xs = [r["n"] for r in records if r["shim_mode"] == mode]
        ys = [r["dec"] / 1024 for r in records if r["shim_mode"] == mode]
        ax.plot(
            xs,
            ys,
            marker="o",
            label=f"--shim-mode={mode}",
            color=COLORS[mode],
            linestyle=LINESTYLES[mode],
            linewidth=2,
        )
    ax.set_xlabel("N (x-jsmn-types)")
    ax.set_ylabel("object size (KB)")
    ax.set_title(f"Size vs. type count (calls/type = {N_CHART_CALLS})")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, format="svg")
    plt.close(fig)


def _plot_by_c(records: list[dict[str, object]], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for mode in MODES:
        xs = [r["calls"] for r in records if r["shim_mode"] == mode]
        ys = [r["dec"] / 1024 for r in records if r["shim_mode"] == mode]
        ax.plot(
            xs,
            ys,
            marker="o",
            label=f"--shim-mode={mode}",
            color=COLORS[mode],
            linestyle=LINESTYLES[mode],
            linewidth=2,
        )
    ax.set_xlabel("C (decode+encode pairs per type)")
    ax.set_ylabel("object size (KB)")
    ax.set_title(f"Size vs. call-site count (N = {C_CHART_N})")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, format="svg")
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--out-dir",
        default=str(HERE),
        help="directory to write SVGs + JSON (default: next to plot.py)",
    )
    p.add_argument(
        "--data",
        help="skip the sweep; load records from this JSON file",
    )
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.data:
        data = json.loads(Path(args.data).read_text())
    else:
        data = _sweep()
        (out_dir / "metrics_data.json").write_text(json.dumps(data, indent=2))

    _plot_by_n(data["by_n"], out_dir / "metrics_n.svg")
    _plot_by_c(data["by_c"], out_dir / "metrics_c.svg")
    print(f"wrote {out_dir / 'metrics_n.svg'}")
    print(f"wrote {out_dir / 'metrics_c.svg'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
