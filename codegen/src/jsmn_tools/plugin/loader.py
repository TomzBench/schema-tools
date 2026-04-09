"""Plugin loader and workspace utilities"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple, Protocol

from jinja2 import Environment
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from jsmn_tools.jsmn import bundle_codegen, extend_codegen
from jsmn_tools.spec import ASYNCAPI_3_0, OPENAPI_3_1, split_draft
from jsmn_tools.walk import JoinConflict, join

RE_CONFIG = re.compile(r"^\.?(jsmnTools|JsmnTools|jsmn-tools).py$")

yaml = YAML(typ="safe")


class InvalidResourceError(Exception):
    """Raised when a schema $id does not match the expected URI format."""


class InvalidPlugin(Exception):
    """Raised when workspace plugin did not return a valid Project."""


class RenderError(Exception):
    """Raised when a template fails to render."""


class BundleResult(NamedTuple):
    openapi: Any | None
    asyncapi: Any | None
    other: list[Any]
    conflicts: list[JoinConflict]


class Plugin(Protocol):
    """Plugin contract for .jsmn-tools.py modules.

    Required:
        collect(config) -> list[Resource]

    Required:
        bundle(config) -> JoinedResources

    Optional:
        jinja(config) -> Environment
    """

    collect: Callable[[dict[str, str]], list[Resource]]
    bundle: Callable[[dict[str, str]], BundleResult]


def load_bundle(*specs: Any) -> BundleResult:
    openapi, asyncapi, other = split_draft(*specs)
    joined = join(*openapi, draft=OPENAPI_3_1)
    joined_a = join(*asyncapi, draft=ASYNCAPI_3_0)
    return BundleResult(
        openapi=joined.value,
        asyncapi=joined_a.value,
        other=other,
        conflicts=[*joined.conflicts, *joined_a.conflicts],
    )


def load_resource(path: Path) -> Resource:
    spec = yaml.load(path)
    if "$id" not in spec:
        spec["$id"] = path.resolve().as_uri()
    return Resource.from_contents(spec, default_specification=DRAFT202012)


def load_plugin(path: Path) -> Plugin:
    spec = importlib.util.spec_from_file_location("_jsmn_config", path)
    if not spec or not spec.loader:
        raise InvalidPlugin(f"Cannot load: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod  # type: ignore[return-value]


def load_plugins(workspace: list[Path]) -> dict[Path, Plugin]:
    # filter all the workspace projects with .jsmn-tools.py in the root
    return {
        project_dir: load_plugin(p)
        for project_dir in workspace
        for p in project_dir.iterdir()
        if RE_CONFIG.match(p.name)
    }


def render(
    *templates: tuple[Path, Path],
    registry: Registry,
    prefix: str = "jsmn_",
    jinja_env: Environment | None = None,
    autoconf: dict[str, str] | None = None,
) -> list[RenderError]:
    if not jinja_env:
        jinja_env = Environment(
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    resolver, bundle = bundle_codegen(registry)
    extend_codegen(jinja_env, bundle, resolver=resolver, prefix=prefix)

    if autoconf is not None:
        jinja_env.globals["autoconf"] = autoconf

    errors: list[RenderError] = []
    for src, dst in templates:
        try:
            tpl = Path(src).read_text(encoding="utf-8")
            rendered = jinja_env.from_string(tpl).render()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(rendered, encoding="utf-8")
        except Exception as e:
            errors.append(RenderError(f"{src}: {e}"))
    return errors
