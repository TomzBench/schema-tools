from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

from jsmn_forge.node import ROOT, Behavior, ConflictPolicy, Location, Node

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class MergeConflict:
    location: Location
    destination: Any
    source: Any


class MergeResult(NamedTuple):
    value: Any
    conflicts: list[MergeConflict]


def _merge_dict(
    dst: dict[str, Any],
    src: dict[str, Any],
    node: Node,
    loc: Location = ROOT,
) -> MergeResult:
    result = dict(dst)
    conflicts: list[MergeConflict] = []
    for k, v in src.items():
        if k not in result:
            result[k] = deepcopy(v)
        else:
            child = node.child(k)
            child_loc = loc.push(k)
            (x, c) = merge(result[k], v, child, child_loc)
            conflicts.extend(c)
            result[k] = x
    return MergeResult(result, conflicts)


def _merge_set_like(
    dst: list[Any],
    src: list[Any],
    sort_key: Callable[[Any], str],
    conflict_policy: ConflictPolicy,
    loc: Location = ROOT,
) -> MergeResult:
    # NOTE sort_key is behaving like an "identity"
    #      convert list into dict for set like symantics
    conflicts: list[MergeConflict] = []
    seen = {sort_key(x): x for x in dst}
    for item in src:
        k = sort_key(item)
        if k not in seen:
            seen[k] = deepcopy(item)
        elif seen[k] != item:
            conflicts.append(MergeConflict(loc, seen[k], item))
            if conflict_policy == ConflictPolicy.REPLACE:
                seen[k] = deepcopy(item)
    return MergeResult(
        sorted(seen.values(), key=sort_key),
        conflicts,
    )


def _merge_list(
    dst: list[Any],
    src: list[Any],
    context: tuple[Node, Behavior],
    loc: Location = ROOT,
) -> MergeResult:
    conflicts: list[MergeConflict] = []
    lresult = list(dst)
    n = min(len(dst), len(src))
    for i in range(n):
        if lresult[i] != src[i]:
            (x, c) = merge(lresult[i], src[i], context, loc.push(str(i)))
            conflicts.extend(c)
            lresult[i] = x
    lresult += [deepcopy(x) for x in src[n:]]
    return MergeResult(lresult, conflicts)


def merge(
    dst: Any,
    src: Any,
    context: tuple[Node, Behavior],
    loc: Location = ROOT,
) -> MergeResult:
    (node, behavior) = context
    if isinstance(dst, dict) and isinstance(src, dict):
        return _merge_dict(dst, src, node, loc)

    if isinstance(dst, list) and isinstance(src, list):
        sort_key, conflict_policy = behavior.sort_key, behavior.conflict_policy
        if sort_key:
            return _merge_set_like(dst, src, sort_key, conflict_policy, loc)
        else:
            return _merge_list(dst, src, context, loc)

    if dst != src:
        v = dst if behavior.conflict_policy == ConflictPolicy.KEEP else src
        return MergeResult(v, [MergeConflict(loc, dst, src)])
    else:
        return MergeResult(dst, [])
