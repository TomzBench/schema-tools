from pathlib import Path
from typing import Any

import pytest
from jsmn_forge.node import Location
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "location"


@pytest.fixture
def resolver() -> Any:
    doc = yaml.load(FIXTURES / "pointer_resolve.yaml")
    res = Resource.from_contents(doc, default_specification=DRAFT202012)
    return (res @ Registry()).resolver()


def _lookup(resolver: Any, loc: Location) -> Any:
    uri = "urn:pointer-test#" + loc.to_pointer()
    return resolver.lookup(uri).contents


def test_ref_plain_nested(resolver: Any) -> None:
    loc = Location(("components", "schemas", "widget", "properties", "name"))
    assert _lookup(resolver, loc) == {"type": "string"}


def test_ref_slash_in_path_key(resolver: Any) -> None:
    loc = Location(("paths", "/items", "get"))
    assert _lookup(resolver, loc)["operationId"] == "listItems"


def test_ref_slash_and_braces_in_path_key(resolver: Any) -> None:
    loc = Location(("paths", "/items/{id}", "get"))
    assert _lookup(resolver, loc)["operationId"] == "getItem"


def test_ref_tilde_in_key(resolver: Any) -> None:
    loc = Location(("x~ext",))
    assert _lookup(resolver, loc) == {"flag": True}


def test_ref_tilde_and_slash_in_key(resolver: Any) -> None:
    loc = Location(("x~/combo",))
    assert _lookup(resolver, loc) == {"ok": True}


def test_ref_deep_defs_nesting(resolver: Any) -> None:
    loc = Location(("$defs", "inner", "$defs", "leaf"))
    assert _lookup(resolver, loc) == {"type": "integer"}


def test_ref_array_index(resolver: Any) -> None:
    loc = Location(("paths", "/items/{id}", "get", "parameters", "0"))
    result = _lookup(resolver, loc)
    assert result["name"] == "id"
    assert result["in"] == "path"
