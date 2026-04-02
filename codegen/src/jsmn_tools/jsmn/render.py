from __future__ import annotations

import re
from pathlib import Path

from jinja2 import (
    ChoiceLoader,
    DictLoader,
    Environment,
    PackageLoader,
)

from .filters import filters, tests
from .prepare import CodegenBundle


class Renderer:
    _env: Environment

    def __init__(
        self,
        compiled: CodegenBundle,
        prefix: str = "jsmn_",
        extra_env: dict[str, str] | None = None,
    ) -> None:
        def read_and_strip(p: Path) -> str:
            return re.sub(
                r'^#include\s+"[^"]*".*\n',
                "",
                p.read_text(encoding="utf-8"),
                flags=re.MULTILINE,
            )

        runtime_dir = Path(__file__).resolve().parent / "runtime"
        runtime_mapping = {
            "jsmn.h": read_and_strip(runtime_dir / "jsmn.h"),
            "runtime.h": read_and_strip(runtime_dir / "runtime.h"),
            "runtime.c": read_and_strip(runtime_dir / "runtime.c"),
        }
        runtime_loader = DictLoader(runtime_mapping)
        package_loader = PackageLoader("jsmn_tools", "jsmn/templates")
        self._env = Environment(
            loader=ChoiceLoader([runtime_loader, package_loader]),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        for name, fn in tests(compiled.original, compiled.resolver).items():
            self._env.tests[name] = fn
        for name, fn in filters(compiled.table, compiled.declarations).items():
            self._env.filters[name] = fn
        descriptors = sorted(compiled.table.values(), key=lambda d: d.key.pos)
        tpl_globals = {
            "prefix": prefix,
            "declarations": compiled.declarations,
            "descriptors": descriptors,
            "strings": compiled.strings,
        }
        self._env.globals.update(tpl_globals)
        if extra_env:
            self._env.globals.update(extra_env)

    def render(self, tpl: str, *, hoist_includes: bool = False) -> str:
        result = self._env.from_string(tpl).render()
        if hoist_includes:
            re_find = r"^#include\s+<[^>]*>.*$"
            re_sub = r"^#include\s+<[^>]*>.*\n"
            seen: set[str] = set()
            for m in re.finditer(re_find, result, re.MULTILINE):
                seen.add(m.group(0))
            body = re.sub(re_sub, "", result, flags=re.MULTILINE)
            result = "\n".join(sorted(seen)) + "\n\n" + body if seen else result
        return result
