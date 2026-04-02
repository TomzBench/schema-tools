from pathlib import Path
from typing import Any

import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from jsmn_tools.jsmn.filters import tests as jinja_tests
from jsmn_tools.jsmn.prepare import codegen

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "render"


@pytest.fixture()
def tag_tests() -> dict[str, Any]:
    spec = FIXTURES / "jsmn-tags.openapi.yaml"
    resource = Resource.from_contents(
        yaml.load(spec), default_specification=DRAFT202012
    )
    registry: Registry[Any] = [resource] @ Registry()
    compiled = codegen(registry)
    return jinja_tests(compiled.original, compiled.resolver)


def _find_decl(tag_tests, compiled_original, name):
    """Find a decl by name from the original declarations."""
    for d in compiled_original:
        if d.ctype.name == name:
            return d
    raise ValueError(f"decl {name} not found")


@pytest.fixture()
def originals() -> list:
    spec = FIXTURES / "jsmn-tags.openapi.yaml"
    resource = Resource.from_contents(
        yaml.load(spec), default_specification=DRAFT202012
    )
    registry: Registry[Any] = [resource] @ Registry()
    return codegen(registry).original


def test_tagged_string(tag_tests, originals) -> None:
    """x-jsmn-tag: 'network' matches 'network', not 'other'."""
    decl = _find_decl(tag_tests, originals, "tagged_string")
    assert tag_tests["tagged"](decl, "network") is True
    assert tag_tests["tagged"](decl, "other") is False


def test_tagged_list(tag_tests, originals) -> None:
    """x-jsmn-tag: ['network', 'config'] matches both."""
    decl = _find_decl(tag_tests, originals, "tagged_list")
    assert tag_tests["tagged"](decl, "network") is True
    assert tag_tests["tagged"](decl, "config") is True
    assert tag_tests["tagged"](decl, "other") is False


def test_tagged_empty_list(tag_tests, originals) -> None:
    """x-jsmn-tag: [] matches nothing."""
    decl = _find_decl(tag_tests, originals, "tagged_empty")
    assert tag_tests["tagged"](decl, "network") is False


def test_tagged_missing(tag_tests, originals) -> None:
    """No x-jsmn-tag on schema matches nothing."""
    decl = _find_decl(tag_tests, originals, "not_tagged")
    assert tag_tests["tagged"](decl, "network") is False
