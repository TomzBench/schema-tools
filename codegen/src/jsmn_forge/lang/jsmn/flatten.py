from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import reduce
from typing import TYPE_CHECKING, Any
from urllib.parse import urldefrag

from jsmn_forge.lang.jsmn.ir import CDecl, CStruct, CType, Dim, Field
from jsmn_forge.node import Location
from jsmn_forge.spec import OPENAPI_3_1, OpenApi31Keys
from jsmn_forge.walk import Step, walk

if TYPE_CHECKING:
    from referencing._core import Resolver


@dataclass
class ConstraintViolation:
    location: Location


@dataclass
class BrokenRef:
    ref: str


type FlattenError = ConstraintViolation | BrokenRef


@dataclass
class FlattenResult:
    decls: dict[CType, CDecl]
    errors: list[FlattenError]


_FORMAT_MAP: dict[str, str] = {
    "uint8": "uint8_t",
    "int8": "int8_t",
    "uint16": "uint16_t",
    "int16": "int16_t",
    "uint32": "uint32_t",
    "int32": "int32_t",
    "uint64": "uint64_t",
    "int64": "int64_t",
    "float": "float",
    "double": "double",
}


class TypeKey(StrEnum):
    NULL = "null"
    BOOL = "bool"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"
    OBJECT = "object"
    ARRAY = "array"


# Walking OpenAPI 3.1 key words
type StepSpec = Step[OpenApi31Keys]


# Filter in all object schemas
def _is_schema(step: StepSpec) -> bool:
    return (
        step.kind == "schema_enter"
        and isinstance(step.value, dict)
        and step.value.get("type") == "object"
        and "x-jsmn-forge-as" in step.value
    )


def _follow_ref(
    schema: Any,
    loc: Location,
    curr_resolver: Resolver,
) -> tuple[Location, Any, Resolver]:
    base, fragment = urldefrag(schema["$ref"])
    if not base:
        base = loc[0]
    location_fragment = Location.from_pointer(fragment)
    target_location = Location.from_segments(base, *location_fragment)
    resolved = curr_resolver.lookup(schema["$ref"])
    return (target_location, resolved.contents, resolved.resolver)


def _seek_ctype(schema: Any, loc: Location, curr_resolver: Resolver) -> CType:  # noqa: PLR0911
    if "$ref" in schema:
        resolved = _follow_ref(schema, loc, curr_resolver)
        (target_location, target_contents, target_resolver) = resolved
        return _seek_ctype(target_contents, target_location, target_resolver)
    ty: TypeKey = schema.get("type")
    assert ty in TypeKey
    match ty:
        case TypeKey.NULL:
            return CType("null")
        case TypeKey.BOOL | TypeKey.BOOLEAN:
            return CType("bool")
        case TypeKey.INTEGER | TypeKey.NUMBER:
            fmt = schema.get("format")
            return CType(_FORMAT_MAP.get(fmt, "int32_t"))
        case TypeKey.STRING:
            max_len = schema.get("maxLength", 0)  # TODO value error
            buf = max_len + 1  # +1 for null terminator
            return CType("char", (Dim(buf, buf),))
        case TypeKey.OBJECT:
            return CType(schema.get("x-jsmn-forge-as", ""))
        case TypeKey.ARRAY:
            min_items = schema.get("minItems", 0)
            max_items = schema.get("maxItems", 0)  # TODO value error
            items = schema.get("items")
            if items is None:
                raise ValueError(f"array without items: {schema}")
            dim = Dim(min_items, max_items)
            inner = _seek_ctype(items, loc, curr_resolver)
            return CType(inner.name, (dim, *inner.dims))


# Walk complex types (objects, arrays, $refs, and (eventually) compositional
def _walk_any(
    schema: Any,
    loc: Location,
    curr_resolver: Resolver,
) -> FlattenResult:
    ty: TypeKey = schema.get("type")
    if ty == "object" and "x-jsmn-forge-as" in schema:
        decls: dict[CType, CDecl] = {}
        errors: list[FlattenError] = []
        fields: list[Field] = []
        properties_location = loc.push("properties")
        required = set(schema.get("required", []))
        for prop_name, prop_schema in schema.get("properties", {}).items():
            prop_loc = properties_location.push(prop_name)
            prop_ctype = _seek_ctype(prop_schema, prop_loc, curr_resolver)
            fields.append(Field(prop_name, prop_ctype, prop_name in required))
            child = _walk_any(prop_schema, prop_loc, curr_resolver)
            decls |= child.decls
            errors.extend(child.errors)
        ctype = CType(schema["x-jsmn-forge-as"])
        decls |= {ctype: CStruct(ctype, loc, fields)}
        return FlattenResult(decls, errors)
    elif ty == "array":
        items = schema.get("items")
        assert items
        prop_loc = loc.push("items")
        return _walk_any(items, prop_loc, curr_resolver)
    elif "$ref" in schema:
        resolved = _follow_ref(schema, loc, curr_resolver)
        (target_location, contents, target_resolver) = resolved
        return _walk_any(contents, target_location, target_resolver)
    elif any(k in schema for k in ("allOf", "anyOf", "oneOf")):
        raise NotImplementedError
    else:
        return FlattenResult({}, [])


# Walk spec and get locations of  all structs
def flatten_with_resolver(*specs: Any, resolver: Resolver) -> FlattenResult:
    def step(acc: FlattenResult, s: StepSpec) -> FlattenResult:
        results = _walk_any(s.value, s.location, resolver)
        decls = {**acc.decls, **results.decls}
        errors = acc.errors + results.errors
        return FlattenResult(decls, errors)

    init = FlattenResult({}, [])
    steps = filter(_is_schema, walk(*specs, draft=OPENAPI_3_1))
    return reduce(step, steps, init)
