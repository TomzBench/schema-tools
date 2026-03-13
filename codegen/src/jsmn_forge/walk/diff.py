from dataclasses import dataclass
from typing import Any

from jsmn_forge.node import ROOT, Location


@dataclass
class Missing:
    value: Any


@dataclass
class Extra:
    value: Any


@dataclass
class MissMatch:
    self: Any
    other: Any


type Diff = Missing | Extra | MissMatch


def _filter_diff[D: Diff](
    diffs: dict[Location, Diff],
    cls: type[D],
) -> dict[Location, D]:
    return {loc: d for loc, d in diffs.items() if isinstance(d, cls)}


def missing(diffs: dict[Location, Diff]) -> dict[Location, Missing]:
    return _filter_diff(diffs, Missing)


def extra(diffs: dict[Location, Diff]) -> dict[Location, Extra]:
    return _filter_diff(diffs, Extra)


def missmatch(diffs: dict[Location, Diff]) -> dict[Location, MissMatch]:
    return _filter_diff(diffs, MissMatch)


def diff(a: Any, b: Any, loc: Location = ROOT) -> dict[Location, Diff]:
    ret: dict[Location, Diff] = {}
    if isinstance(a, dict) and isinstance(b, dict):
        for k in (*a, *(k for k in b if k not in a)):
            key: Location = loc.push(k)
            if k not in b:
                ret[key] = Missing(a[k])
            elif k not in a:
                ret[key] = Extra(b[k])
            else:
                nested = diff(a[k], b[k], key)
                if nested:
                    ret |= nested
        return ret
    elif isinstance(a, list) and isinstance(b, list):
        n = min(len(a), len(b))
        for i in range(n):
            nested = diff(a[i], b[i], loc.push(str(i)))
            if nested:
                ret |= nested
        ret |= {loc.push(str(i)): Missing(a[i]) for i in range(n, len(a))}
        ret |= {loc.push(str(i)): Extra(b[i]) for i in range(n, len(b))}
        return ret
    elif a != b:
        return {loc: MissMatch(a, b)}
    else:
        return {}
