# metrics

Data collection + charts for the `Runtime` section of the docs.

## Regenerate the charts

```console
$ uv sync --group docs
$ cd examples/metrics
$ uv run python plot.py --out-dir ../../docs/_static
```

Writes three files:

- `docs/_static/metrics_n.svg`        — size vs. N (types), C=1
- `docs/_static/metrics_c.svg`        — size vs. C (calls/type), N=100
- `docs/_static/metrics_data.json`    — raw sweep data

Commit all three.

## Measure a single data point

```console
$ uv run python measure.py                     # default N sweep
$ uv run python measure.py 100                 # single N
$ uv run python measure.py 1 10 100            # custom sweep
$ uv run python measure.py --calls 3           # 3 decode+encode pairs/type
$ uv run python measure.py --shim-mode none    # polymorphic API
$ uv run python measure.py --shared-names      # string-pool best case
$ uv run python measure.py --json out.json     # structured output
```

Flags compose. Prints `size` columns; `--json` also writes a record array.

## Files

- `sensor.yaml.jinja` — N-schema OpenAPI spec template
- `main.c.jinja` — harness rendered by `jsmn render`
- `measure.py` — renders, compiles, runs `size`; supports `--shim-mode`,
  `--calls`, `--shared-names`, `--json`
- `plot.py` — sweeps modes × N × C via `measure.py`, renders SVGs
