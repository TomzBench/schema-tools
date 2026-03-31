from typing import Any

from jsmn_tools.node import ROOT, Behavior, Location, Node, Ref

# TODO cache anchors and strip duplicates
def normalize(
    obj: dict[str, Any],
    context: tuple[Node, Behavior],
    loc: Location = ROOT,
    *,
    scheme: str | None = None,
) -> dict[str, Any]:
    suffix = f".{context[0].kind}.yaml"
    return _normalize(obj, context, loc, scheme=scheme, suffix=suffix)


def _normalize(
    obj: Any,
    context: tuple[Node, Behavior],
    loc: Location,
    *,
    scheme: str | None,
    suffix: str,
) -> Any:
    (node, behavior) = context
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, val in obj.items():
            if key == "$ref" and not node.opaque:
                out[key] = (
                    Ref(val).normalize(scheme or "forge", suffix)
                    if isinstance(val, str)
                    else val
                )
            else:
                out[key] = _normalize(
                    val,
                    node.child(key),
                    loc.push(key),
                    scheme=scheme,
                    suffix=suffix,
                )
        return out
    if isinstance(obj, list):
        sort_key = behavior.sort_key
        items = [
            _normalize(
                item, context, loc.push(str(i)), scheme=scheme, suffix=suffix
            )
            for i, item in enumerate(obj)
        ]
        return sorted(items, key=sort_key) if sort_key else items
    return obj
