from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import Environment
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from jsmn_tools.node import ObjectNode, SchemeURI
from jsmn_tools.plugin.loader import (
    BundleResult,
    InvalidResourceError,
    load_plugins,
)
from jsmn_tools.spec import ASYNCAPI_3_0, OPENAPI_3_1, parse_draft, split_draft
from jsmn_tools.walk import join, prefixer

type Specs[T] = dict[ObjectNode | None, list[T]]

yaml = YAML(typ="safe")

RE_AUTOCONF = re.compile(r"^#define\s(\S+)\s?(\S+)?$", flags=re.MULTILINE)


def _require_west():
    try:
        from west import util
        from west.manifest import Manifest
    except ImportError:
        raise ImportError(
            "Missing west. Install with: pip install jsmn-tools[zephyr]"
        )
    return util, Manifest


def parse_autoconfig(build_dir: Path) -> dict[str, str]:
    autoconf = Path(f"{build_dir}/zephyr/include/generated/zephyr/autoconf.h")
    if not autoconf.is_absolute():
        raise ValueError("build dir must be absolute path")
    with Path.open(autoconf) as file:
        config = {k: v for k, v in RE_AUTOCONF.findall(file.read())}
        config["CMAKE_BINARY_DIR"] = build_dir
    return config


def parse_workspace() -> list[Path]:
    util, Manifest = _require_west()
    topdir = Path(util.west_topdir())
    manifest = Manifest.from_topdir(topdir)
    dirs = [topdir / p.path for p in manifest.projects if manifest.is_active(p)]
    return list(dict.fromkeys(p.resolve() for p in dirs))


# REVIEW: per-module grouping may be dead code. The flat join
# (load_zephyr_bundle) merges all modules into 1-per-draft, and normalize
# rewrites scheme $refs to relative paths before join. The per-module
# Registry produced by join_zephyr_registry has broken cross-module ref
# resolution anyway (relative file paths don't match scheme $ids).
# Keep until atx-zdk migration confirms the flat path works end-to-end.
def split_uri(*content: Any) -> dict[SchemeURI, list[Any]]:
    schemes: dict[SchemeURI, list[Any]] = defaultdict(list)
    for c in content:
        uri = SchemeURI.parse(c["$id"])
        if uri is None:
            raise InvalidResourceError(f"Invalid scheme URI: {c['$id']}")
        schemes[uri].append(c)
    return schemes


# REVIEW: see split_uri comment — this function and load_zephyr_registry
# build a per-module Registry that is likely unnecessary. The flat join
# via load_zephyr_bundle produces a working Registry for codegen.
#
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
#   - jsmn/flatten.py   _follow_ref()
#     (workaround: reconstructs full URI from loc[0])
#   - jsmn/filters.py   json_pointer()
#     (exposed to templates, currently only receives full URIs)
def join_zephyr_registry(specs: dict[SchemeURI, list[Any]]) -> Registry:
    res = []
    for uri, items in specs.items():
        openapi, asyncapi, other = split_draft(*items)
        joined = join(*openapi, draft=OPENAPI_3_1)
        joined_a = join(*asyncapi, draft=ASYNCAPI_3_0)
        for conflict in [*joined.conflicts, *joined_a.conflicts]:
            print(f"warning: [{conflict.id}] @ {conflict.location}")
        if joined.value:
            id = SchemeURI(uri.scheme, uri.module, "openapi", uri.version)
            joined.value["$id"] = str(id)
            res.append(joined.value)
        if joined_a.value:
            id_a = SchemeURI(uri.scheme, uri.module, "asyncapi", uri.version)
            joined_a.value["$id"] = str(id_a)
            res.append(joined_a.value)
        res.extend([o for o in other if "$id" in o])
    return res @ Registry()


def load_zephyr_resource(
    path: Path,
    module: str,
    name: str,
    ver: int,
    prefix: str | None = None,
) -> Any:
    spec = yaml.load(path)
    # NOTE: $id is used by join() for conflict labels (spec identification),
    # not for registry resolution. Normalize rewrites $ref values by pattern
    # matching the scheme, independent of $id.
    uri = SchemeURI("zephyr", module, name, ver)
    spec["$id"] = str(uri)
    if prefix and (draft := parse_draft(spec)):
        spec = prefixer(spec, draft=draft, prefix=prefix)
    return Resource.from_contents(spec, DRAFT202012)


def load_zephyr_resources(build_dir: Path) -> list[Resource]:
    workspace = parse_workspace()
    plugins = load_plugins(workspace)
    config = {"build_dir": str(build_dir)}
    return [r for plugin in plugins.values() for r in plugin.collect(config)]


def load_zephyr_bundle(build_dir: Path) -> BundleResult:
    resources = load_zephyr_resources(build_dir)
    specs = [r.contents for r in resources]
    openapi, asyncapi, other = split_draft(*specs)
    joined = join(*openapi, draft=OPENAPI_3_1)
    joined_a = join(*asyncapi, draft=ASYNCAPI_3_0)
    return BundleResult(
        openapi=joined.value,
        asyncapi=joined_a.value,
        other=other,
        conflicts=[*joined.conflicts, *joined_a.conflicts],
    )


def load_zephyr_jinja(build_dir: Path) -> Environment:
    autoconf = parse_autoconfig(build_dir)
    workspace = parse_workspace()
    plugins = load_plugins(workspace)
    env = Environment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    for plugin in plugins.values():
        extend = getattr(plugin, "extend", None)
        if extend:
            extend(env)
    env.globals["autoconf"] = autoconf
    return env
