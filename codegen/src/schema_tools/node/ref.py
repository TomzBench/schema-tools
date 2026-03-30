from __future__ import annotations

import re
from dataclasses import dataclass

_SCHEME_RE = re.compile(
    r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9-]*)://"
    r"(?P<module>[a-zA-Z0-9_-]+)/"
    r"(?P<resource>[a-zA-Z0-9_-]+)/"
    r"v(?P<version>\d+)"
    r"(?:#(?P<fragment>.*))?$"
)


@dataclass(frozen=True)
class Ref:
    raw: str

    @property
    def is_local(self) -> bool:
        return self.raw.startswith("#")

    @property
    def is_relative(self) -> bool:
        return self.raw.startswith("./")

    def normalize(self, scheme: str) -> str:
        if self.is_local:
            return self.raw
        if self.is_relative:
            # TODO: relative ref without fragment (e.g. "./file.yaml") is likely
            # an authoring mistake — pass through unchanged and warn when
            # logging is available.
            idx = self.raw.find("#")
            return self.raw[idx:] if idx != -1 else self.raw
        m = _SCHEME_RE.match(self.raw)
        if m and m.group("scheme") == scheme:
            module = m.group("module")
            fragment = m.group("fragment")
            base = f"./{module}.openapi.yaml"
            return f"{base}#{fragment}" if fragment else base
        return self.raw
