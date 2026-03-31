# schema-tools

[![CI](https://github.com/altronix/schema-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/altronix/schema-tools/actions/workflows/ci.yml)

A code generator for JSON parsing in C.

## Testing

```bash
uv run pytest                        # unit + integration
uv run pytest --cov=schema_tools     # with coverage
uv run pytest codegen/tests/unit     # unit only
uv run radon cc codegen/src -a -nb   # cyclomatic complexity
uv run radon mi codegen/src -nb      # maintainability index
```

# Building the docs

## Prerequisites

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv venv
uv sync --extra docs
```

## Build

```bash
uv run sphinx-build -b html docs docs/_build
```

## Preview

```bash
uv run python -m http.server 8000 --directory docs/_build
```

Open [http://localhost:8000](http://localhost:8000).
