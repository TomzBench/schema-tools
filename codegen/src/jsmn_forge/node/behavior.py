from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class ConflictPolicy(Enum):
    KEEP = auto()
    REPLACE = auto()


@dataclass(frozen=True)
class Behavior:
    sort_key: Callable[[Any], str] | None
    conflict_policy: ConflictPolicy = ConflictPolicy.KEEP


_NO_BHV = Behavior(sort_key=None)

SortKey = Callable[[Any], str]


def canonical(x: Any) -> str:
    """Canonical sort key for any JSON value."""
    return json.dumps(x, sort_keys=True)


def identity_key(*fields: str) -> SortKey:
    """Create a sort key from identity fields of a dict."""
    def key(x: Any) -> str:
        if isinstance(x, dict):
            return "\x00".join(x.get(f, "") for f in fields)
        return canonical(x)
    return key


def sort_set(arr: list) -> list:
    """Canonical sort for set-like arrays.

    Handles primitives, objects, mixed types.
    For: required, enum, type, tags, examples,
    allOf, oneOf, anyOf, security."""
    return sorted(arr, key=canonical)


def sort_set_by(arr: list[dict], *keys: str) -> list[dict]:
    """Sort object arrays by identity key fields.
    For: parameters (name, in)."""
    return sorted(arr, key=identity_key(*keys))
