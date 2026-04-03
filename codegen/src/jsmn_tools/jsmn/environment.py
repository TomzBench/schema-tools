from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import ChoiceLoader, DictLoader, PackageLoader
from jinja2 import Environment as JinjaEnvironment
from referencing import Registry, Resource

from .descriptor import Descriptors, Key
from .filters import filters, tests
from .flatten import flatten_with_resolver
from .ir import CDecl
from .prepare import (
    build_tables,
    extend_declarations,
    sort_declarations,
)
from jsmn_tools.spec import ASYNCAPI_3_0, OPENAPI_3_1

if TYPE_CHECKING:
    from referencing._core import Resolver


def _read_and_strip(p: Path) -> str:
    return re.sub(
        r'^#include\s+"[^"]*".*\n',
        "",
        p.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )


@dataclass(frozen=True)
class Environment:
    original: list[CDecl]
    declarations: list[CDecl]
    table: dict[Key, Descriptors]
    strings: list[tuple[int, str]]
    resolver: Resolver

    @classmethod
    def empty(cls) -> Environment:
        reg = Registry()
        return cls([], [], {}, [], reg.resolver())

    @classmethod
    def from_specifications(cls, *resources: Resource) -> Environment:
        registry = resources @ Registry()
        resolver = registry.resolver()
        openapi = [
            r.contents for r in registry.values() if "openapi" in r.contents
        ]
        asyncapi = [
            r.contents for r in registry.values() if "asyncapi" in r.contents
        ]
        flattened = flatten_with_resolver(
            *openapi,
            resolver=resolver,
            draft=OPENAPI_3_1,
        )
        flattened |= flatten_with_resolver(
            *asyncapi,
            resolver=resolver,
            draft=ASYNCAPI_3_0,
        )
        sorted_user = sort_declarations(flattened.decls)
        extended = extend_declarations(sorted_user)
        strings, table = build_tables(sorted_user)

        return Environment(
            original=sorted_user,
            declarations=extended,
            table=table,
            strings=list(strings.strings()),
            resolver=resolver,
        )

    def extend(
        self,
        other: JinjaEnvironment,
        prefix: str | None = None,
    ) -> None:
        runtime_dir = Path(__file__).resolve().parent / "runtime"
        runtime_mapping = {
            "jsmn.h": _read_and_strip(runtime_dir / "jsmn.h"),
            "runtime.h": _read_and_strip(runtime_dir / "runtime.h"),
            "runtime.c": _read_and_strip(runtime_dir / "runtime.c"),
        }
        runtime_loader = DictLoader(runtime_mapping)
        package_loader = PackageLoader("jsmn_tools", "jsmn/templates")
        if isinstance(other.loader, ChoiceLoader):
            loaders = [*other.loader.loaders, runtime_loader, package_loader]
        elif other.loader is not None:
            loaders = [other.loader, runtime_loader, package_loader]
        else:
            loaders = [runtime_loader, package_loader]
        other.loader = ChoiceLoader(loaders)
        other.tests.update(tests(self.original, self.resolver))
        other.filters.update(
            filters(self.table, self.declarations, self.resolver)
        )
        descriptors = sorted(self.table.values(), key=lambda d: d.key.pos)
        tpl_globals = {
            "declarations": self.declarations,
            "descriptors": descriptors,
            "strings": self.strings,
        }
        if prefix:
            tpl_globals |= {"prefix": prefix}
        other.globals.update(tpl_globals)
