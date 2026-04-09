from __future__ import annotations

import re
from dataclasses import dataclass

_PASSTHROUGH_SCHEMES = frozenset({"http", "https", "file"})

_RE = re.compile(
    r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9-]*)"
    r"://(?P<module>[a-zA-Z0-9_-]+)"
    r"/(?P<name>[a-zA-Z0-9_-]+)"
    r"/v(?P<version>\d+)"
    r"(?:#(?P<fragment>.*))?$"
)


@dataclass(frozen=True)
class SchemeURI:
    scheme: str
    module: str
    name: str
    version: int
    fragment: str | None = None

    def __str__(self) -> str:
        base = f"{self.scheme}://{self.module}/{self.name}/v{self.version}"
        return f"{base}#{self.fragment}" if self.fragment else base

    @property
    def is_passthrough(self) -> bool:
        return self.scheme in _PASSTHROUGH_SCHEMES

    @classmethod
    def parse(cls, uri: str) -> SchemeURI | None:
        m = _RE.match(uri)
        if not m:
            return None
        return cls(
            scheme=m["scheme"],
            module=m["module"],
            name=m["name"],
            version=int(m["version"]),
            fragment=m["fragment"],
        )
