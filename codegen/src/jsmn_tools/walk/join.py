# Join = normalize + merge

from dataclasses import dataclass
from functools import reduce
from typing import Any, NamedTuple

from jsmn_tools.node import Behavior, Location, ObjectNode

from .merge import MergeConflict, merge
from .normalize import normalize


@dataclass
class JoinConflict:
    id: str
    location: Location
    destination: Any
    source: Any


@dataclass
class JoinResult:
    value: Any
    conflicts: list[JoinConflict]


class Specification(NamedTuple):
    id: str
    data: Any


def upgrade_conflict(id: str):
    def upgrader(conflict: MergeConflict) -> JoinConflict:
        return JoinConflict(
            id=id,
            location=conflict.location,
            destination=conflict.destination,
            source=conflict.source,
        )

    return upgrader


def join[E: str](*specs: dict, draft: ObjectNode[E]) -> JoinResult:
    root = (draft, Behavior(sort_key=None))

    normalized = [
        Specification(
            id=spec.get("$id", f"spec:{i}"),
            data=normalize(spec, root),
        )
        for i, spec in enumerate(specs)
    ]

    def merge_step(acc: JoinResult, spec: Specification) -> JoinResult:
        (id, src) = spec
        (r, c) = merge(acc.value, src, root)
        conflicts = list(map(upgrade_conflict(id), c))
        return JoinResult(r, acc.conflicts + conflicts)

    rest = iter(normalized)
    try:
        (_, first) = next(rest)
        return reduce(merge_step, rest, JoinResult(first, []))
    except StopIteration:
        return JoinResult({}, [])
