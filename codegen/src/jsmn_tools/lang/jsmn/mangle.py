from __future__ import annotations

from functools import reduce
from typing import TYPE_CHECKING

from .ir import CStruct, CType, CUnion, Dim, Field, FixedDims, Variant

if TYPE_CHECKING:
    from collections.abc import Iterator

    from jsmn_tools.node import Location


def mangle(ctype: CType | tuple[Variant, ...], optional: bool = False) -> str:
    if not isinstance(ctype, CType):
        variants = sorted(mangle(v.ctype) for v in ctype)
        return f"union{len(ctype)}__{'__'.join(variants)}"
    else:

        def reducer(acc: str, next: Dim | FixedDims) -> str:
            if isinstance(next, FixedDims):
                d = "x".join(str(dim.max) for dim in next.dims)
                return f"{acc}__d{d}"
            else:
                return f"vla__{acc}__n{next.max}"

        base = ctype.as_primitive() or ctype.name
        result = reduce(reducer, ctype.dim_groups(), base)
        return f"optional__{result}" if optional else result


def dim_walk(ctype: CType) -> Iterator[tuple[Dim | FixedDims, CType]]:
    inner = CType(ctype.name)
    for group in ctype.dim_groups():
        if isinstance(group, FixedDims):
            inner = CType(inner.name, group.dims)
            yield (group, inner)
        else:
            spec = CType(inner.name, (group, *inner.dims))
            yield (group, spec)
            inner = CType(mangle(spec))


def make_optional(inner: CType, loc: Location) -> CStruct:
    ctype = CType(mangle(inner, optional=True))
    present = Field("present", CType("bool"))
    maybe = Field("maybe", CType(mangle((Variant("value", inner),))))
    return CStruct(ctype, loc, [present, maybe])


def make_maybe(inner: CType, loc: Location) -> CUnion:
    variants = (Variant("value", inner),)
    ctype = CType(mangle(variants))
    return CUnion(ctype, loc, [Variant("value", inner)])


def make_vla(ctype: CType, loc: Location, *, name: str | None = None) -> CStruct:
    cap = ctype.dims[0].max
    rest = ctype.dims[1:]
    return CStruct(
        CType(name if name is not None else mangle(ctype)),
        loc,
        [
            Field("len", CType("uint32_t")),
            Field("_pad", CType("uint8_t", (Dim(4, 4),))),
            Field("items", CType(ctype.name, (Dim(cap, cap), *rest))),
        ],
    )
