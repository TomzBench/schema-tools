# Join = normalize + merge

from collections.abc import Callable
from dataclasses import dataclass
from functools import reduce
from pathlib import Path
from typing import Any, NamedTuple

from ruamel.yaml import YAML

from jsmn_forge.node import Behavior, Location, ObjectNode

from .merge import MergeConflict, merge
from .normalize import normalize

yaml = YAML(typ="safe")


@dataclass
class JoinConflict:
    file: Path
    location: Location
    destination: Any
    source: Any


@dataclass
class JoinResult:
    value: Any
    conflicts: list[JoinConflict]
    errors: list[FileNotFoundError]


type NormalizeResult = tuple[list[Specification], list[FileNotFoundError]]


class Specification(NamedTuple):
    file: Path
    data: Any


def upgrade_conflict(file: Path) -> Callable[[MergeConflict], JoinConflict]:
    def upgrader(conflict: MergeConflict) -> JoinConflict:
        return JoinConflict(
            file=file,
            location=conflict.location,
            destination=conflict.destination,
            source=conflict.source,
        )

    return upgrader


def join[E: str](
    *args: Path,
    scheme: str | None = None,
    draft: ObjectNode[E],
) -> JoinResult:
    root = (draft, Behavior(sort_key=None))

    def sort_step(acc: NormalizeResult, next: Path) -> NormalizeResult:
        try:
            behavior_sorted = normalize(yaml.load(next), root, scheme=scheme)
            spec = Specification(next, behavior_sorted)
            acc[0].append(spec)
        except FileNotFoundError as e:
            acc[1].append(e)
        return acc

    def merge_step(acc: JoinResult, spec: Specification) -> JoinResult:
        (file, src) = spec
        (r, c) = merge(acc.value, src, root)
        conflicts = list(map(upgrade_conflict(file), c))
        # TODO evaluate conflicts. Upgrade some to errors
        #      (ie: info.version missmatch)
        return JoinResult(r, acc.conflicts + conflicts, [])

    # Behavior sort all the input files
    init: NormalizeResult = ([], [])
    (behavior_sorted, errors) = reduce(sort_step, args, init)

    rest = iter(behavior_sorted)
    try:
        # Pop the first specification off the list for which merge will appy
        (_, first) = next(rest)
        # Merge remaining specifications
        result = reduce(merge_step, rest, JoinResult(first, [], errors))
        return result
    except StopIteration as _e:
        return JoinResult(None, [], errors)
