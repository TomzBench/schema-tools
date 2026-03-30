from __future__ import annotations

from typing import Any


class Location(tuple):
    """Document location as a tuple of path segments.

    Convertible to/from JSON Pointer (RFC 6901).
    """

    def to_pointer(self) -> str:
        if not self:
            return ""
        return "/" + "/".join(
            s.replace("~", "~0").replace("/", "~1") for s in self
        )

    @classmethod
    def from_pointer(cls, pointer: str) -> Location:
        if not pointer or pointer == "/":
            return cls()
        segments = pointer.lstrip("/").split("/")
        return cls(s.replace("~1", "/").replace("~0", "~") for s in segments)

    @classmethod
    def from_segments(cls, *segments: str) -> Location:
        return cls(segments)

    def push(self, key: str) -> Location:
        return Location((*self, key))

    def resolve(self, doc: Any) -> Any:
        node = doc
        for key in self:
            node = node[key]
        return node


ROOT = Location()
