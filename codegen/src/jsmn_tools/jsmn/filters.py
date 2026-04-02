from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .descriptor import (
    ArrayDescriptor,
    ArrayKind,
    Descriptors,
    FieldDescriptor,
    Key,
    StructDescriptor,
)
from .ir import (
    CArray,
    CDecl,
    CEnum,
    CStruct,
    CType,
    CUnion,
    Dim,
    Variant,
)
from .primitives import Primitive

if TYPE_CHECKING:
    from collections.abc import Callable

    from referencing._core import Resolver


# ── Rendering maps ────────────────────────────────────────────────────

_PRIM_KINDS: dict[Primitive, str] = {
    Primitive.BOOL: "JT_KIND_BOOL",
    Primitive.CHAR: "JT_KIND_CHAR",
    Primitive.UINT8: "JT_KIND_U8",
    Primitive.INT8: "JT_KIND_I8",
    Primitive.UINT16: "JT_KIND_U16",
    Primitive.INT16: "JT_KIND_I16",
    Primitive.UINT32: "JT_KIND_U32",
    Primitive.INT32: "JT_KIND_I32",
    Primitive.UINT64: "JT_KIND_U64",
    Primitive.INT64: "JT_KIND_I64",
    Primitive.FLOAT: "JT_KIND_FLOAT",
    Primitive.DOUBLE: "JT_KIND_DOUBLE",
}
assert _PRIM_KINDS.keys() == set(Primitive), "missing primitive kind"

_ARRAY_KINDS: dict[ArrayKind, str] = {
    ArrayKind.FIXED: "JT_KIND_FIXED",
    ArrayKind.STRING: "JT_KIND_STRING",
    ArrayKind.VLA: "JT_KIND_VLA",
}


def tests(
    user_decls: list[CDecl],
    resolver: Resolver,
) -> dict[str, Callable[..., Any]]:
    cdecl_index = {v.ctype.name: v for v in user_decls}
    array_names = {v.ctype.name for v in user_decls if isinstance(v, CArray)}

    def is_struct_decl(decl: CDecl) -> bool:
        return isinstance(decl, CStruct)

    def is_union_decl(decl: CDecl) -> bool:
        return isinstance(decl, CUnion)

    def is_enum_decl(decl: CDecl) -> bool:
        return isinstance(decl, CEnum)

    def is_array_decl(decl: CDecl | CType) -> bool:
        name = decl.name if isinstance(decl, CType) else decl.ctype.name
        return name in array_names

    def is_user_decl(decl: CDecl | CType) -> bool:
        t = decl.name if isinstance(decl, CType) else decl.ctype.name
        return t in cdecl_index

    def is_union_ctype(ctype: CType | tuple[Variant, ...]) -> bool:
        return not isinstance(ctype, CType)

    # Tag lookup is a single resolver hit — no recursion. The decl's
    # location points to the schema where x-jsmn-generate was found,
    # and x-jsmn-tag must be co-located on that same schema. Tags on
    # $ref targets or allOf branches are not inherited. A future
    # validation pass could warn when x-jsmn-tag appears on a schema
    # without x-jsmn-generate (misplaced tag).
    def is_tagged(decl: CDecl, tag: str) -> bool:
        try:
            spec_id = decl.loc[0]
            resolved = resolver.lookup(spec_id)
            path = type(decl.loc)(decl.loc[1:])
            schema = path.resolve(resolved.contents)
            tags = schema.get("x-jsmn-tag", [])
            if isinstance(tags, str):
                tags = [tags]
            return tag in tags
        except (KeyError, IndexError, LookupError):
            return False

    return {
        "struct_decl": is_struct_decl,
        "union_decl": is_union_decl,
        "enum_decl": is_enum_decl,
        "array_decl": is_array_decl,
        "user_decl": is_user_decl,
        "union_ctype": is_union_ctype,
        "tagged": is_tagged,
    }


def filters(
    table: dict[Key, Descriptors],
    decls: list[CDecl],
) -> dict[str, Callable[..., Any]]:
    """Return all template filters (stateless + table-rendering closures)."""
    # ── Build struct index for positional lookups ─────────────────────
    struct_index: dict[str, int] = {
        d.ctype.name: d.key.pos
        for d in table.values()
        if isinstance(d, StructDescriptor)
    }

    cdecl_index = {v.ctype.name: v for v in decls}

    def qualifier(ctype: CType) -> str:
        qual = cdecl_index.get(ctype.name)
        if qual is None:
            return ""
        elif isinstance(qual, CUnion):
            return "union"
        elif isinstance(qual, CArray):
            return ""
        else:
            return "struct"

    def _resolve_ctype(ctype: CType) -> str:
        try:
            return f"JT_PRIM({_PRIM_KINDS[Primitive(ctype.name)]})"
        except ValueError:
            return f"JT_STRUCT({struct_index[ctype.name]})"

    def _resolve_ref(ref: Key | CType) -> str:
        if isinstance(ref, CType):
            return _resolve_ctype(ref)
        return f"JT_ARRAY({ref.pos})"

    def dimensions(dims: tuple[Dim, ...]) -> str:
        return "".join(f"[{d.max}]" for d in dims)

    # ── Table-rendering closures ──────────────────────────────────────

    def name_offset(f: FieldDescriptor) -> str:
        return str(f.name_offset)

    def value_offset(f: FieldDescriptor) -> str:
        parent = table[f.parent]
        base = f"offsetof(struct {parent.ctype.name}, {f.name})"
        if f.optional:
            return f"{base} + offsetof(struct {f.ctype.name}, maybe)"
        return base

    def present_offset(f: FieldDescriptor) -> str:
        if not f.optional:
            return "0xFFFF"
        parent = table[f.parent]
        return f"offsetof(struct {parent.ctype.name}, {f.name})"

    def size_expr(s: StructDescriptor) -> str:
        return f"sizeof(struct {s.ctype.name})"

    def type_expr(f: FieldDescriptor) -> str:
        return _resolve_ref(f.type_ref)

    def elem_expr(a: ArrayDescriptor) -> str:
        return _resolve_ref(a.elem)

    def elem_size(a: ArrayDescriptor) -> str:
        if isinstance(a.elem, CType):
            if a.elem.name in Primitive:
                return f"sizeof({a.elem.name})"
            return f"sizeof(struct {a.elem.name})"
        child = table[a.elem]
        assert isinstance(child, ArrayDescriptor)
        if child.kind in (ArrayKind.FIXED, ArrayKind.STRING):
            return "0"
        # VLA child — stride is the wrapper struct size
        return f"sizeof(struct {child.ctype.name})"

    def array_kind(a: ArrayDescriptor) -> str:
        return _ARRAY_KINDS[a.kind]

    # ── Comment filter ─────────────────────────────────────────────────

    def comment(d: Descriptors) -> str:
        loc = d.loc.to_pointer()
        if isinstance(d, StructDescriptor):
            return f"{d.ctype.name} @ {loc}"
        elif isinstance(d, FieldDescriptor):
            parent = table[d.parent]
            opt = " (optional)" if d.optional else ""
            return f"{parent.ctype.name}.{d.name}{opt} @ {loc}"
        else:
            return f"{d.kind.name.lower()} {d.ctype.name} max={d.max} @ {loc}"

    # ── Descriptor-list filters (used in template iteration) ─────────

    def structs(ds: list[Descriptors]) -> list[StructDescriptor]:
        return [d for d in ds if isinstance(d, StructDescriptor)]

    def fields(ds: list[Descriptors]) -> list[FieldDescriptor]:
        return [d for d in ds if isinstance(d, FieldDescriptor)]

    def arrays(ds: list[Descriptors]) -> list[ArrayDescriptor]:
        return [d for d in ds if isinstance(d, ArrayDescriptor)]

    result: dict[str, Callable[..., Any]] = {
        "dimensions": dimensions,
        "comment": comment,
        "name_offset": name_offset,
        "value_offset": value_offset,
        "present_offset": present_offset,
        "size_expr": size_expr,
        "type_expr": type_expr,
        "elem_expr": elem_expr,
        "elem_size": elem_size,
        "array_kind": array_kind,
        "structs": structs,
        "fields": fields,
        "arrays": arrays,
        "qualifier": qualifier,
    }

    return result
