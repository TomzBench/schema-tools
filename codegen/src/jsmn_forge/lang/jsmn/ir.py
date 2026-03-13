"""C IR — output of the flatten pass, input to C codegen.

Core types:

  CType   — hashable type identifier: (name, dims)
  Dim     — array dimension with min/max bounds
  Variant — named variant inside a tagged union
  Field   — struct member: name + CType (or tuple[Variant,...] for union)

Codegen declarations (CDecl = CStruct | CUnion | CEnum):

  CStruct — named struct definition with fields
  CUnion  — named union definition with variants
  CEnum   — named enum definition with labels

Everything else — VLA wrappers, optional wrappers, union wrappers, mangled
names, token counts, dependency order — is derived by codegen from these types.

A CType with dims where min != max implies a VLA wrapper struct.
A Field with required=False implies an optional wrapper struct.
A Field with tuple[Variant, ...] implies a tagged union wrapper.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING, NamedTuple

from .primitives import Primitive

if TYPE_CHECKING:
    from jsmn_forge.node import Location

_PRIMITIVE_MANGLE: dict[Primitive, str] = {
    Primitive.UINT8: "u8",
    Primitive.INT8: "i8",
    Primitive.UINT16: "u16",
    Primitive.INT16: "i16",
    Primitive.UINT32: "u32",
    Primitive.INT32: "i32",
    Primitive.UINT64: "u64",
    Primitive.INT64: "i64",
    Primitive.FLOAT: "f32",
    Primitive.DOUBLE: "f64",
    Primitive.BOOL: "bool",
    Primitive.CHAR: "char",
}
assert _PRIMITIVE_MANGLE.keys() == set(Primitive), "missing primitive mangle"


class Dim(NamedTuple):
    """Array dimension — one level in a (possibly multi-dimensional) array.

    Outer-to-inner order: dims[0] is the outermost array.
    min == max → fixed dimension (e.g., char name[32])
    min != max → variable length array (capacity = max)
    """

    min: int
    max: int


class FixedDims(NamedTuple):
    dims: tuple[Dim, ...]


class StringDim(FixedDims):
    """Trailing fixed dims on a char type (string buffer)."""


class CType(NamedTuple):
    """Hashable C type identifier.

    name: resolved C type name — "bool", "uint32_t", "char", "foo"
    dims:  array shape, outer-to-inner

    Examples:
        CType("uint32_t")                      → uint32_t (scalar)
        CType("char", (Dim(32, 32),))          → char[32] (string)
        CType("uint8_t", (Dim(64, 64),))       → uint8_t[64] (byte array)
        CType("uint32_t", (Dim(0, 3),))        → vla wrapper (VLA, capacity 3)
        CType("foo")                            → struct foo (ref)
        CType("foo", (Dim(0, 10),))            → vla wrapper of struct foo
    """

    name: str
    dims: tuple[Dim, ...] = ()

    @property
    def is_primitive(self) -> bool:
        return self.name in Primitive

    # NOTE implementation may simplify if when flatten.py builds dimensions,
    #      store dimensions as inner-to-outer instead of outer-to-inner. We
    #      could then iterate naturally instead of doing full dim traversal.
    #      Manglers (2) can then traverse naturally, and templates for type
    #      names would reverse in the filter.
    def dim_groups(self) -> list[Dim | FixedDims | StringDim]:
        """Return dimension groups inner-to-outer.

        Groups consecutive fixed dims (min==max) into FixedDims.
        Trailing fixed dims on char types become StringDim.
        VLA dims (min!=max) are yielded individually.
        """
        result: list[Dim | FixedDims | StringDim] = []
        count = len(self.dims)
        i = 0
        while i < count:
            if self.dims[i].min != self.dims[i].max:
                result.append(self.dims[i])
                i += 1
            else:
                j = i
                while j < count and self.dims[j].min == self.dims[j].max:
                    j += 1
                group = self.dims[i:j]
                if self.name == "char" and j == count:
                    result.append(StringDim(group))
                else:
                    result.append(FixedDims(group))
                i = j
        result.reverse()
        return result

    def as_primitive(self) -> str | None:
        try:
            return _PRIMITIVE_MANGLE[Primitive(self.name)]
        except ValueError:
            return None

    def dim_walk(self) -> Iterator[tuple[Dim | FixedDims, CType]]:
        """Walk dim groups inner-to-outer, yielding accumulated CTypes.

        FixedDims: yields (group, inner) — inner has fixed dims absorbed.
        VLA dim:   yields (dim, spec)   — spec ready for _make_vla.
        """
        inner = CType(self.name)
        for group in self.dim_groups():
            if isinstance(group, FixedDims):
                inner = CType(inner.name, group.dims)
                yield (group, inner)
            else:
                spec = CType(inner.name, (group, *inner.dims))
                yield (group, spec)
                inner = CType(spec.mangle())

    def mangle(self, optional: bool = False) -> str:
        def reducer(acc: str, next: Dim | FixedDims) -> str:
            if isinstance(next, FixedDims):
                d = "x".join(str(dim.max) for dim in next.dims)
                return f"{acc}__d{d}"
            else:
                return f"vla__{acc}__n{next.max}"

        base = self.as_primitive() or self.name
        result = reduce(reducer, self.dim_groups(), base)
        return f"optional__{result}" if optional else result


class Variant(NamedTuple):
    """Named variant inside a tagged union.

    name:  field name inside the union body (e.g., "foo" in `struct foo foo;`)
    ctype: the variant's C type
    """

    name: str
    ctype: CType


@dataclass
class Field:
    """Struct member.

    When ctype is a tuple of Variants, the field is a tagged union.
    Codegen derives the union wrapper and its mangled name from the
    variant list.
    """

    name: str
    ctype: CType | tuple[Variant, ...]
    required: bool = True


@dataclass
class CStruct:
    """Named C struct definition — the primary codegen unit."""

    ctype: CType
    loc: Location
    fields: list[Field]


@dataclass
class CUnion:
    """Named C union definition."""

    ctype: CType
    loc: Location
    variants: list[Variant]


@dataclass
class CEnum:
    """Named C enum definition."""

    ctype: CType
    loc: Location
    labels: list[str]


type CDecl = CStruct | CUnion | CEnum
