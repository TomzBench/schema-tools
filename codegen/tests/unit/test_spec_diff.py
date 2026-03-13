from jsmn_forge.node import sort_set, sort_set_by
from jsmn_forge.walk import Extra, Missing, MissMatch, diff


def test_identical_returns_empty() -> None:
    a = {"x": 1, "y": [1, 2]}
    assert diff(a, a) == {}


def test_top_level_missing_and_extra() -> None:
    a = {"a": 1}
    b = {"b": 2}
    result = diff(a, b)
    assert result == {
        ("a",): Missing(1),
        ("b",): Extra(2),
    }


def test_top_level_mismatch() -> None:
    a = {"a": 1}
    b = {"a": 2}
    result = diff(a, b)
    assert result == {("a",): MissMatch(1, 2)}


def test_nested_dict_diff() -> None:
    a = {"info": {"title": "Foo", "version": "1.0"}}
    b = {"info": {"title": "Bar", "version": "1.0"}}
    result = diff(a, b)
    assert result == {("info", "title"): MissMatch("Foo", "Bar")}


def test_nested_dict_missing_key() -> None:
    a = {"info": {"title": "Foo", "desc": "hello"}}
    b = {"info": {"title": "Foo"}}
    result = diff(a, b)
    assert result == {("info", "desc"): Missing("hello")}


def test_list_extra_element() -> None:
    a = {"tags": ["api"]}
    b = {"tags": ["api", "v2"]}
    result = diff(a, b)
    assert result == {("tags", "1"): Extra("v2")}


def test_list_missing_element() -> None:
    a = {"tags": ["api", "v1"]}
    b = {"tags": ["api"]}
    result = diff(a, b)
    assert result == {("tags", "1"): Missing("v1")}


def test_list_of_dicts() -> None:
    a = {"params": [{"name": "id", "in": "path"}]}
    b = {"params": [{"name": "id", "in": "query"}]}
    result = diff(a, b)
    assert result == {("params", "0", "in"): MissMatch("path", "query")}


def test_type_mismatch_scalar_vs_dict() -> None:
    a = {"x": "string"}
    b = {"x": {"type": "string"}}
    result = diff(a, b)
    assert result == {("x",): MissMatch("string", {"type": "string"})}


def test_sort_set_strings() -> None:
    assert sort_set(["c", "a", "b"]) == ["a", "b", "c"]


def test_sort_set_mixed_types() -> None:
    arr = [True, "alpha", 1, None]
    assert sort_set(arr) == sort_set(list(reversed(arr)))


def test_sort_set_objects() -> None:
    a = [{"z": 1, "a": 2}, {"m": 3}]
    b = [{"m": 3}, {"a": 2, "z": 1}]
    assert sort_set(a) == sort_set(b)


def test_sort_set_by() -> None:
    arr = [
        {"k1": "b", "k2": "x", "other": 1},
        {"k1": "a", "k2": "y", "other": 2},
    ]
    result = sort_set_by(arr, "k1", "k2")
    assert result[0]["k1"] == "a"
    assert result[1]["k1"] == "b"
