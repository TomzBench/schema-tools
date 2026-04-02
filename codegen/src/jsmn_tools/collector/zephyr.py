"""Zephyr spec collector"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Callable
from functools import reduce
from pathlib import Path
from typing import Any, NamedTuple, TypedDict, TypeGuard

from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML


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


def parse_workspace(
    build_dir: str,
    extra: dict[str, str] | None = None,
) -> tuple[list[Path], dict[str, str]]:
    autoconf = Path(f"{build_dir}/zephyr/include/generated/zephyr/autoconf.h")
    if not autoconf.is_absolute():
        raise ValueError("build dir must be absolute path")
    with open(autoconf) as file:
        config = {k: v for k, v in RE_AUTOCONF.findall(file.read())}
        config["CMAKE_BINARY_DIR"] = build_dir
    util, Manifest = _require_west()
    topdir = Path(util.west_topdir())
    manifest = Manifest.from_topdir(topdir)
    return (
        [topdir / p.path for p in manifest.projects if manifest.is_active(p)],
        config | extra if extra else config,
    )


class InvalidResourceError(Exception):
    """Raised when a schema $id does not match the expected URI format."""


class InvalidPlugin(Exception):
    """Raised when workspace plugin did not return a valid Project."""


type CollectErrors = InvalidResourceError | InvalidPlugin


class Project(TypedDict):
    module: str
    version: int
    specs: dict[str, str]


class CollectResult(NamedTuple):
    registry: Registry
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

    def resource_loader(
        prj_dir: Path,
        module: str,
        version: int,
    ) -> Callable[[list[Resource], tuple[str, str]], list[Resource]]:
        def load_resource(
            acc: list[Resource],
            kv: tuple[str, str],
        ) -> list[Resource]:
            name, path = kv
            content = yaml.load(prj_dir / path)
            if "$id" not in content:
                content["$id"] = f"zephyr://{module}/{name}/v{version}"
                res = Resource.from_contents(content, DRAFT202012)
                acc.append(res)
            elif RE_URI.match(content["$id"]):
                res = Resource.from_contents(content, DRAFT202012)
                acc.append(res)
            else:
                raise InvalidResourceError(f"Invalid $id: {content['$id']}")
            return acc

        return load_resource

    resources: list[Resource] = []
    errors: list[CollectErrors] = []

    # filter all the workspace projects with .jsmn-tools.py in the root
    projects = [
        (project_dir, p)
        for project_dir in workspace
        for p in project_dir.iterdir()
        if RE_CONFIG.match(p.name)
    ]

    for project_dir, config_file in projects:
        try:
            prj = load_plugin(config_file, config)
        except Exception as e:
            errors.append(InvalidPlugin(str(e)))
            continue
        module = prj["module"]
        version = prj["version"]
        specs = prj["specs"].items()
        load_resource = resource_loader(project_dir, module, version)
        try:
            resources += reduce(load_resource, specs, [])
        except Exception as e:
            errors.append(InvalidResourceError(str(e)))
            continue

    return CollectResult(resources @ Registry(), errors)
