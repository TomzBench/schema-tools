from pathlib import Path
from typing import Any

import pytest
from jsmn_tools.jsmn.flatten import flatten_with_resolver
from jsmn_tools.jsmn.ir import CArray, CStruct, CType, Dim
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
        CType("top_array"),
        CType("top_array_item"),
        CType("top_arr_ref"),
        CType("ref_prop"),
        CType("ref_nested"),
        CType("arr_ref_items"),
        CType("ref_to_array"),
        CType("arr_ref_nested"),
        CType("target_a"),
        CType("target_b"),
        CType("target_b_child"),
        CType("target_c_item"),
        CType("allof_inline"),
        CType("allof_with_props"),
        CType("allof_ref"),
        CType("allof_nested"),
        CType("allof_nested_child"),
        CType("allof_required"),
        CType("top_string"),
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


def test_flatten_top_level_array_inline(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("top_array")]
    assert isinstance(decl, CArray)
    assert decl.elem == CType("top_array_item")
    assert decl.min == 0
    assert decl.max == 5
    # items object also collected as a struct
    item_decl = result.decls[CType("top_array_item")]
    assert isinstance(item_decl, CStruct)


def test_flatten_top_level_array_ref(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("top_arr_ref")]
    assert isinstance(decl, CArray)
    assert decl.elem == CType("target_a")
    assert decl.min == 0
    assert decl.max == 8


def test_flatten_top_level_string(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("top_string")]
    assert isinstance(decl, CArray)
    assert decl.elem == CType("char")
    assert decl.min == 33  # maxLength(32) + 1
    assert decl.max == 33


def test_flatten_allof_inline(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("allof_inline")]
    assert isinstance(decl, CStruct)
    assert len(decl.fields) == 2
    assert decl.fields[0].name == "alpha"
    assert decl.fields[0].ctype == CType("uint32_t")
    assert decl.fields[1].name == "beta"
    assert decl.fields[1].ctype == CType("bool")


def test_flatten_allof_with_own_props(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("allof_with_props")]
    assert isinstance(decl, CStruct)
    field_names = [f.name for f in decl.fields]
    assert "merged" in field_names
    assert "own" in field_names


def test_flatten_allof_ref_branch(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("allof_ref")]
    assert isinstance(decl, CStruct)
    field_names = [f.name for f in decl.fields]
    assert "id" in field_names
    assert "extra" in field_names


def test_flatten_allof_nested_child(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("allof_nested")]
    assert isinstance(decl, CStruct)
    assert decl.fields[0].name == "child"
    assert decl.fields[0].ctype == CType("allof_nested_child")
    # nested child also collected
    child = result.decls[CType("allof_nested_child")]
    assert isinstance(child, CStruct)


def test_flatten_allof_required_union(registry: Registry) -> None:
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    decl = result.decls[CType("allof_required")]
    assert isinstance(decl, CStruct)
    by_name = {f.name: f for f in decl.fields}
    assert by_name["from_parent"].required is True
    assert by_name["from_branch"].required is True
