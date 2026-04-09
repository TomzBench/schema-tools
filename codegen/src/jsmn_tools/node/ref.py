from __future__ import annotations

from dataclasses import dataclass

from jsmn_tools.node.uri import SchemeURI


@dataclass(frozen=True)
class Ref:
    raw: str

    @property
    def is_local(self) -> bool:
        return self.raw.startswith("#")

    @property
    def is_relative(self) -> bool:
        return self.raw.startswith("./")

    def normalize(self, suffix: str) -> str:
        if self.is_local:
            return self.raw
        if self.is_relative:
            # TODO: relative ref without fragment (e.g. "./file.yaml") is likely
            # an authoring mistake — pass through unchanged and warn when
            # logging is available.
            idx = self.raw.find("#")
            return self.raw[idx:] if idx != -1 else self.raw
        uri = SchemeURI.parse(self.raw)
        if uri and not uri.is_passthrough:
            base = f"./{uri.module}{suffix}"
            return f"{base}#{uri.fragment}" if uri.fragment else base
        return self.raw
