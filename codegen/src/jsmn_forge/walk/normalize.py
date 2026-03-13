from typing import Any

from jsmn_forge.node import ROOT, Behavior, Location, Node, Ref


# TODO cache anchors and strip duplicates
def normalize(
    obj: Any,
    context: tuple[Node, Behavior],
    loc: Location = ROOT,
    *,
    scheme: str | None = None,
) -> Any:
    (node, behavior) = context
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, val in obj.items():
            if key == "$ref" and not node.opaque:
                out[key] = (
                    Ref(val).normalize(scheme or "forge")
                    if isinstance(val, str)
                    else val
                )
            else:
                out[key] = normalize(
                    val,
                    node.child(key),
                    loc.push(key),
                    scheme=scheme,
                )
        return out
    if isinstance(obj, list):
        sort_key = behavior.sort_key
        items = [
            normalize(item, context, loc.push(str(i)), scheme=scheme)
            for i, item in enumerate(obj)
        ]
        return sorted(items, key=sort_key) if sort_key else items
    return obj
