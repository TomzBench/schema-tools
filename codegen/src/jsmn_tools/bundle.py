"""Workspace parsing utilities"""

import re
from pathlib import Path
from typing import NamedTuple, TypedDict, cast

from jsonschema import validate  # type: ignore[import-untyped]
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

# safe yaml loader for schemas
yaml = YAML(typ="safe")

# regex for finding jsmn-tools file
RE_CONFIG = re.compile(r"^\.?(jsmnTools|JsmnTools|jsmn-tools).ya?ml$")

# regex for validating $id URIs: scheme://module/resource/vN
RE_URI = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9-]*://[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/v\d+$"
)


# validator support
SCHEMA = yaml.load("""
    type: object
    required: [resources]
    properties:
        resources:
            type: array
            items:
                type: object
                required: [name, version]
                properties:
                    name:
                        type: string
                    version:
                        type: number
                    openapi:
                        type: array
                        items:
                            type: string
                    asyncapi:
                        type: array
                        items:
                            type: string
                    if:
                        type: array
                        items:
                            type: string
""")


class ResourceConfig(TypedDict):
    name: str
    version: int
    openapi: list[Path]
    asyncapi: list[Path]


class Config(TypedDict):
    name: str
    resources: list[ResourceConfig]


class Uri(NamedTuple):
    module: str
    resource: str
    version: int


def _parse_workspace(path: Path | str, config: Path) -> Config:
    root = Path(path).absolute()
    name = root.name.split(".")[0]
    doc = yaml.load(root / config)
    validate(instance=doc, schema=SCHEMA)
    doc["name"] = name
    for res in doc["resources"]:
        if "openapi" in res:
            res["openapi"] = [root / path for path in res["openapi"]]
        else:
            res["openapi"] = []
        if "asyncapi" in res:
            res["asyncapi"] = [root / path for path in res["asyncapi"]]
        else:
            res["asyncapi"] = []
    return cast("Config", doc)


class InvalidUriError(Exception):
    """Raised when a schema $id does not match the expected URI format."""


def _read_resource(
    loc: str | Path,
    scheme: str,
    module: str,
    res: str,
    version: int,
) -> Resource:
    content = yaml.load(loc)
    if "$id" not in content:
        content["$id"] = f"{scheme}://{module}/{res}/v{version}"
    elif not RE_URI.match(content["$id"]):
        # TODO need to collect errors instead of failing fast
        raise InvalidUriError("Invalid $id: \"content['$id']\"")
    return Resource.from_contents(content, default_specification=DRAFT202012)


def bundle(scheme: str, workspace: list[Path] | list[str]) -> Registry:
    """ """

    # iterate over workspace directories, parsing specifications
    configs = [
        _parse_workspace(module, path)
        for module in workspace
        for path in Path(module).iterdir()
        if RE_CONFIG.match(path.name)
    ]

    # flatten resources into a keyable registry
    content = [
        _read_resource(spec, scheme, cfg["name"], res["name"], res["version"])
        for cfg in configs
        for res in cfg["resources"]
        for spec in [*res["openapi"], *res["asyncapi"]]
    ]
    return content @ Registry()
