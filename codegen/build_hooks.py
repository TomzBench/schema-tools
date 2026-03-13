"""Hatch build hook — amalgamate C runtime into the package tree."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from hatchling.builders.hooks.plugin.interface import (  # type: ignore[import-not-found]
    BuildHookInterface,
)


def _load_amalgamate(p: Path) -> Callable[[], str]:
    spec = importlib.util.spec_from_file_location("amalgamate", p)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.amalgamate  # type: ignore[no-any-return]


class CustomBuildHook(BuildHookInterface):  # type: ignore[misc]
    PLUGIN_NAME = "custom"

    def initialize(self, _version: str, _build_data: dict[str, Any]) -> None:
        mod = Path(__file__).resolve().parent / "src" / "jsmn_forge"
        amalg = mod / "amalgamate.py"
        output = mod / "lang" / "c" / "runtime" / "jsmn_forge_amalg.c"
        amalgamate = _load_amalgamate(amalg)
        blob = amalgamate()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(blob, encoding="utf-8")
