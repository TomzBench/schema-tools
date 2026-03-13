from pathlib import Path
from typing import Any

import pytest
from jsmn_forge.lang.jsmn.flatten import flatten_with_resolver
from jsmn_forge.lang.jsmn.ir import CStruct, CType, Dim
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "flatten"


@pytest.fixture
def registry() -> Registry:
    specs = [FIXTURES / "spec_a.yaml", FIXTURES / "spec_b.yaml"]
    resources = [
        Resource.from_contents(yaml.load(p), default_specification=DRAFT202012)
        for p in specs
    ]
    registry: Registry[Any] = resources @ Registry()
    return registry


def test_flatten_collects_all_structs(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    assert result.decls.keys() == {
        CType("standalone"),
        CType("parent"),
        CType("parent_child"),
        CType("array_host"),
        CType("array_item"),
        CType("deep_array_host"),
        CType("deep_array_entry"),
        CType("deep_array_detail"),
        CType("ref_prop"),
        CType("ref_nested"),
        CType("arr_ref_items"),
        CType("ref_to_array"),
        CType("arr_ref_nested"),
        CType("target_a"),
        CType("target_b"),
        CType("target_b_child"),
        CType("target_c_item"),
    }


def test_flatten_ref_resolved(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("ref_prop")]
    assert isinstance(decl, CStruct)
    assert decl.fields[0].ctype == CType("target_a")


def test_flatten_array_dims(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("array_host")]
    assert isinstance(decl, CStruct)
    assert decl.fields[0].ctype == CType("array_item", (Dim(0, 10),))
