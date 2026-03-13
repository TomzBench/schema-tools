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
from .ir import CType, Dim, Field, FixedDims, Variant
from .primitives import Primitive

if TYPE_CHECKING:
    from collections.abc import Callable


# ── Rendering maps ────────────────────────────────────────────────────

_PRIM_KINDS: dict[Primitive, str] = {
    Primitive.BOOL: "RT_KIND_BOOL",
    Primitive.CHAR: "RT_KIND_CHAR",
    Primitive.UINT8: "RT_KIND_U8",
    Primitive.INT8: "RT_KIND_I8",
    Primitive.UINT16: "RT_KIND_U16",
    Primitive.INT16: "RT_KIND_I16",
    Primitive.UINT32: "RT_KIND_U32",
    Primitive.INT32: "RT_KIND_I32",
    Primitive.UINT64: "RT_KIND_U64",
    Primitive.INT64: "RT_KIND_I64",
    Primitive.FLOAT: "RT_KIND_FLOAT",
    Primitive.DOUBLE: "RT_KIND_DOUBLE",
}
assert _PRIM_KINDS.keys() == set(Primitive), "missing primitive kind"

_ARRAY_KINDS: dict[ArrayKind, str] = {
    ArrayKind.FIXED: "RT_KIND_FIXED",
    ArrayKind.STRING: "RT_KIND_STRING",
    ArrayKind.VLA: "RT_KIND_VLA",
}


# ── Stateless filters (header rendering) ─────────────────────────────


def mangle(ctype: CType | tuple[Variant, ...]) -> str:
    if not isinstance(ctype, CType):
        variants = sorted(mangle(v.ctype) for v in ctype)
        return f"union{len(ctype)}__{'__'.join(variants)}"
    else:
        return ctype.mangle()


def qualifier(ctype: CType | tuple[Variant, ...]) -> str:
    if not isinstance(ctype, CType):
        return "union"
    elif any(d.min != d.max for d in ctype.dims) or not ctype.is_primitive:
        return "struct"
    else:
        return ""


def dimensions(dims: tuple[Dim, ...]) -> str:
    return "".join(f"[{d.max}]" for d in dims)


def _decl(ctype: CType, name: str) -> str:
    """Render a C field declaration from a CType and field name."""
    if qual := qualifier(ctype):
        if (groups := ctype.dim_groups()) and isinstance(groups[-1], FixedDims):
            leading = groups[-1]
            n = len(leading.dims)
            inner = CType(ctype.name, ctype.dims[n:])
            dims = dimensions(leading.dims)
            return f"{qualifier(inner)} {mangle(inner)} {name}{dims}"
        else:
            return f"{qual} {mangle(ctype)} {name}"
    else:
        return f"{ctype.name} {name}{dimensions(ctype.dims)}"


def field(f: Field | Variant) -> str:
    if isinstance(f, Variant):
        return _decl(f.ctype, f.name)
    elif not f.required:
        return f"struct optional__{mangle(f.ctype)} {f.name}"
    elif not isinstance(f.ctype, CType):
        return f"union {mangle(f.ctype)} {f.name}"
    else:
        return _decl(f.ctype, f.name)


# ── Factory ───────────────────────────────────────────────────────────


def filters(table: dict[Key, Descriptors]) -> dict[str, Callable[..., Any]]:
    """Return all template filters (stateless + table-rendering closures)."""
    result: dict[str, Callable[..., Any]] = {
        "field": field,
        "mangle": mangle,
        "qualifier": qualifier,
        "dimensions": dimensions,
    }

    # ── Build struct index for positional lookups ─────────────────────
    struct_index: dict[str, int] = {
        d.ctype.name: d.key.pos
        for d in table.values()
        if isinstance(d, StructDescriptor)
    }

    def _resolve_ctype(ctype: CType) -> str:
        try:
            return f"RT_PRIM({_PRIM_KINDS[Primitive(ctype.name)]})"
        except ValueError:
            return f"RT_STRUCT({struct_index[ctype.name]})"

    def _resolve_ref(ref: Key | CType) -> str:
        if isinstance(ref, CType):
            return _resolve_ctype(ref)
        return f"RT_ARRAY({ref.pos})"

    # ── Table-rendering closures ──────────────────────────────────────

    def name_offset(f: FieldDescriptor) -> str:
        return str(f.name_offset)

    def value_offset(f: FieldDescriptor) -> str:
        parent = table[f.parent]
        base = f"offsetof(struct {parent.ctype.name}, {f.name})"
        if f.optional:
            wrapper = f"optional__{mangle(f.ctype)}"
            return f"{base} + offsetof(struct {wrapper}, maybe)"
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
        return f"sizeof(struct {child.ctype.mangle()})"

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

    result.update(
        {
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
        }
    )

    return result
