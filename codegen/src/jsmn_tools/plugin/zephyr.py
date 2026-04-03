"""Zephyr workspace plugin"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple, NotRequired, TypedDict, TypeGuard

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


class JinjaFilterExists(Exception):
    """Raised when a plugin declares a filter that already exists."""


class JinjaTestExists(Exception):
    """Raised when a plugin declares a test that already exists."""


class RenderError(Exception):
    """Raised when a template fails to render."""


type CollectErrors = (
    InvalidResourceError
    | InvalidPlugin
    | JinjaFilterExists
    | JinjaTestExists
    | RenderError
)


class Project(TypedDict):
    module: str
    version: int
    specs: dict[str, str]
    render: NotRequired[list[tuple[str, str]]]
    jinja_filters: NotRequired[dict[str, Callable[..., Any]]]
    jinja_tests: NotRequired[dict[str, Callable[..., bool]]]
    jinja_globals: NotRequired[dict[str, Any]]


class LoadedProject(Project):
    dir: Path


class CollectResult(NamedTuple):
    registry: Registry
    projects: list[LoadedProject]
    errors: list[CollectErrors]


def collect(workspace: list[Path], config: dict[str, str]) -> CollectResult:
    def is_project(obj: Any) -> TypeGuard[Project]:
        keys = ("module", "version", "specs")
        return isinstance(obj, dict) and all(k in obj for k in keys)

    def load_plugin(path: Path, config: dict[str, str]) -> Any:
        spec = importlib.util.spec_from_file_location("_jsmn_config", path)
        if not spec or not spec.loader:
            raise InvalidPlugin(f"Cannot load: {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        prj = mod.collect(config)
        if not is_project(prj):
            raise InvalidPlugin(str(path))
        return prj

    resources: list[Resource] = []
    loaded_projects: list[LoadedProject] = []
    errors: list[CollectErrors] = []

    # filter all the workspace projects with .jsmn-tools.py in the root
    configs = [
        (project_dir, p)
        for project_dir in workspace
        for p in project_dir.iterdir()
        if RE_CONFIG.match(p.name)
    ]

    for project_dir, config_file in configs:
        try:
            prj = load_plugin(config_file, config)
        except Exception as e:
            errors.append(InvalidPlugin(str(e)))
            continue
        prj["dir"] = config_file.parent
        module = prj["module"]
        version = prj["version"]
        specs = prj["specs"].items()
        loaded_projects.append(prj)
        for name, path in specs:
            content = yaml.load(project_dir / path)
            if "$id" not in content:
                content["$id"] = f"zephyr://{module}/{name}/v{version}"
                res = Resource.from_contents(content, DRAFT202012)
                resources.append(res)
            elif RE_URI.match(content["$id"]):
                res = Resource.from_contents(content, DRAFT202012)
                resources.append(res)
            else:
                e = InvalidResourceError(f"Invalid $id: {content['$id']}")
                errors.append(e)

    return CollectResult(resources @ Registry(), loaded_projects, errors)


def _add_prefix_to_registry(prefix: str, registry: Registry) -> Registry:
    resources: list[Resource] = []
    for r in registry.values():
        if d := parse_draft(r.contents):
            contents = prefixer(r.contents, draft=d, prefix=prefix)
            resources.append(Resource.from_contents(contents, DRAFT202012))
        else:
            resources.append(r)
    return resources @ Registry()


def render(
    result: CollectResult,
    prefix: str = "jsmn_",
    type_prefix: str = "",
    autoconf: dict[str, str] | None = None,
) -> list[CollectErrors]:
    errors: list[CollectErrors] = []
    jinja_env = JinjaEnvironment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # -- pass 1: accumulate custom filters, tests, and globals from plugins --
    if autoconf is not None:
        jinja_env.globals["autoconf"] = autoconf
    for prj in result.projects:
        module = prj["module"]
        for name, fn in prj.get("jinja_filters", {}).items():
            if name in jinja_env.filters:
                errors.append(JinjaFilterExists(f"'{name}' from '{module}'"))
            else:
                jinja_env.filters[name] = fn
        for name, fn in prj.get("jinja_tests", {}).items():
            if name in jinja_env.tests:
                errors.append(JinjaTestExists(f"'{name}' from '{module}'"))
            else:
                jinja_env.tests[name] = fn
        jinja_env.globals.update(prj.get("jinja_globals", {}))

    # -- pass 2: apply type prefix and build environment --------------------
    registry = result.registry
    if type_prefix:
        registry = _add_prefix_to_registry(type_prefix, registry)

    jsmn_env = Environment.from_specifications(*registry.values())
    jsmn_env.extend(jinja_env, prefix=prefix)
    for prj in [p for p in result.projects if "render" in p]:
        prj_dir = prj["dir"]
        for src, dst in prj["render"]:
            src_path = prj_dir / src
            dst_path = Path(dst) if Path(dst).is_absolute() else prj_dir / dst
            try:
                tpl = src_path.read_text(encoding="utf-8")
                rendered = jinja_env.from_string(tpl).render()
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                dst_path.write_text(rendered, encoding="utf-8")
            except Exception as e:
                errors.append(RenderError(f"{src}: {e}"))
    return errors
