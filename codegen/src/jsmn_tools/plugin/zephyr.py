"""Zephyr workspace plugin"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple, NotRequired, Protocol, TypedDict

from jinja2 import Environment as JinjaEnvironment
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from jsmn_tools.jsmn import Environment
from jsmn_tools.spec import parse_draft
from jsmn_tools.walk import prefixer


def _require_west():
    try:
        from west import util
        from west.manifest import Manifest
    except ImportError:
        raise ImportError(
            "Missing west. Install with: pip install jsmn-tools[zephyr]"
        )
    return util, Manifest


# safe yaml loader for schemas
yaml = YAML(typ="safe")

RE_AUTOCONF = re.compile(r"^#define\s(\S+)\s?(\S+)?$", flags=re.MULTILINE)
RE_CONFIG = re.compile(r"^\.?(jsmnTools|JsmnTools|jsmn-tools).py$")
RE_URI = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9-]*://[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/v\d+$"
)


def parse_autoconfig(build_dir: str) -> dict[str, str]:
    autoconf = Path(f"{build_dir}/zephyr/include/generated/zephyr/autoconf.h")
    if not autoconf.is_absolute():
        raise ValueError("build dir must be absolute path")
    with open(autoconf) as file:
        config = {k: v for k, v in RE_AUTOCONF.findall(file.read())}
        config["CMAKE_BINARY_DIR"] = build_dir
    return config


def parse_workspace() -> list[Path]:
    util, Manifest = _require_west()
    topdir = Path(util.west_topdir())
    manifest = Manifest.from_topdir(topdir)
    return [topdir / p.path for p in manifest.projects if manifest.is_active(p)]


class InvalidResourceError(Exception):
    """Raised when a schema $id does not match the expected URI format."""


class InvalidPlugin(Exception):
    """Raised when workspace plugin did not return a valid Project."""


class RenderError(Exception):
    """Raised when a template fails to render."""


class Project(TypedDict):
    module: str
    version: int
    specs: dict[str, str]
    prefix: NotRequired[str]
    render: NotRequired[list[tuple[str, str]]]


class Plugin(Protocol):
    collect: Callable[[dict[str, str]], Project]
    extend: Callable[[JinjaEnvironment], None] | None


def _load_plugin(path: Path) -> Plugin:
    spec = importlib.util.spec_from_file_location("_jsmn_config", path)
    if not spec or not spec.loader:
        raise InvalidPlugin(f"Cannot load: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod  # type: ignore[return-value]


def _load_resource(name: str, path: Path, prj: Project) -> Resource:
    content = yaml.load(path)
    module = prj["module"]
    version = prj["version"]
    prefix = prj.get("prefix", "")
    if "$id" not in content:
        content["$id"] = f"zephyr://{module}/{name}/v{version}"
    elif not RE_URI.match(content["$id"]):
        raise InvalidResourceError(f"Invalid $id: {content['$id']}")
    if prefix and (draft := parse_draft(content)):
        content = prefixer(content, draft=draft, prefix=prefix)
    return Resource.from_contents(content, DRAFT202012)


def _normalize(root: Path, path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else root / path


class Collection(NamedTuple):
    registry: Registry
    environment: JinjaEnvironment
    render: list[tuple[Path, Path]]


def collect(workspace: list[Path], config: dict[str, str]) -> Collection:
    # filter all the workspace projects with .jsmn-tools.py in the root
    plugins = {
        project_dir: _load_plugin(p)
        for project_dir in workspace
        for p in project_dir.iterdir()
        if RE_CONFIG.match(p.name)
    }

    # Get all the project plugins
    projects = {
        project_dir: plugin.collect(config)
        for project_dir, plugin in plugins.items()
    }

    # For each project, load all the resources
    resources = [
        _load_resource(name, project_dir / path, project)
        for project_dir, project in projects.items()
        for name, path in project["specs"].items()
    ]

    # build a jinja env
    jinja_env = JinjaEnvironment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # for each project, extend jinja with project jinja extensions
    for p in plugins.values():
        extend = getattr(p, "extend", None)
        if extend:
            extend(jinja_env)

    # TODO: LIMITATION: The registry is built without a retrieve callback
    # or document-scoped resolvers, so fragment-only $refs (e.g.,
    # "#/components/schemas/foo") cannot be resolved by the global
    # resolver — it has no base_uri context. Full URIs work fine.
    #
    # Fix: use Registry(retrieve=...) with a zephyr:// aware callback,
    # and create resolvers via registry.resolver(base_uri=...) so
    # fragment-only refs resolve against the current document's $id.
    #
    # Call sites to validate when fixed:
    #   - jsmn/flatten.py   _follow_ref()    (workaround: reconstructs full URI from loc[0])
    #   - jsmn/filters.py   json_pointer()   (exposed to templates, currently only receives full URIs)
    return Collection(
        registry=resources @ Registry(),
        environment=jinja_env,
        render=[
            (_normalize(project_dir, src), _normalize(project_dir, dst))
            for project_dir, p in projects.items()
            if "render" in p
            for src, dst in p["render"]
        ],
    )


def render(
    collection: Collection,
    prefix: str = "jsmn_",
    autoconf: dict[str, str] | None = None,
) -> list[RenderError]:
    jinja_env = collection.environment
    if autoconf is not None:
        jinja_env.globals["autoconf"] = autoconf

    jsmn_env = Environment.from_specifications(*collection.registry.values())
    jsmn_env.extend(jinja_env, prefix=prefix)

    errors: list[RenderError] = []
    for src, dst in collection.render:
        try:
            tpl = src.read_text(encoding="utf-8")
            rendered = jinja_env.from_string(tpl).render()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(rendered, encoding="utf-8")
        except Exception as e:
            errors.append(RenderError(f"{src}: {e}"))
    return errors
