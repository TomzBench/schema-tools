# id -> 2 bit tag: xx1 primitive (bits[15:1] = scalar id)
#                  000 struct    (bits[15:2] idx to struct[])
#                  100 array     (bits[15:2] idx to array[])
# NOTE current optional handling "dots into" the offset of assumed wrapper types
# confusing but works. ie: offsetof(struct parent, count) is a pointer to "present" field
# more natural to possibly just store idx of wrapper types into the structs, but decoder has
# to set the "present" field. so perhaps parent should manage the present field and recurse
# into values... (evaluate when implementing runtime.c)
# nameblob[]
# rt_array[]   comment, kind, min, max, elem_size, desc_idx
# rt_field[]   comment, off_name, off_value, off_present, desc_idx
# rt_struct[]  comment, nfields, size, ntoks, field0
# RT_{{struct.name | upper}}_IDX {{idx}}
# RT_{{struct.name | upper}}_TOK {{idx}}
# a "stateful walker", ie: curr struct idx increments toks each field.
#   nesting resets tok counter.
#   parent adds child toks
#   cache descriptor when complete.


from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum, auto
from functools import reduce
from typing import NamedTuple

from jsmn_forge.node import Location

from .ir import CStruct, CType, Dim, Field, FixedDims, StringDim


class Table(Enum):
    STRUCT = auto()
    FIELD = auto()
    ARRAY = auto()


class ArrayKind(Enum):
    FIXED = auto()
    STRING = auto()
    VLA = auto()

    @classmethod
    def from_group(cls, group: Dim | FixedDims) -> ArrayKind:
        return (
            ArrayKind.VLA
            if not isinstance(group, FixedDims)
            else ArrayKind.STRING
            if isinstance(group, StringDim)
            else ArrayKind.FIXED
        )


class Key(NamedTuple):
    table: Table
    pos: int


@dataclass
class Descriptor:
    key: Key
    loc: Location
    ntoks: int
    ctype: CType


@dataclass
class StructDescriptor(Descriptor):
    """All context for rendering a struct entry in a struct rt_struct"""

    """Number of fields"""
    nfields: int
    """Position of first field in fields table"""
    field0: int


@dataclass
class FieldDescriptor(Descriptor):
    """All context for rendering a field entry in a struct rt_field"""

    """Field name (needed for offsetof expressions)"""
    name: str
    """Index of name in string blob"""
    name_offset: int
    """Pointer to parent"""
    parent: Key
    """Field is optional, and wrapped in a synthetic wrapper type"""
    optional: bool
    """Type reference: CType for primitive/struct, Key for array."""
    type_ref: Key | CType


@dataclass
class ArrayDescriptor(Descriptor):
    """All context for rendering an array entry in a struct rt_array"""

    """Array kind: FIXED, STRING, or VLA"""
    kind: ArrayKind
    """Maximum size of elements in the array."""
    max: int
    """Child array Key, or leaf CType"""
    elem: Key | CType


class Strings:
    """String blob"""

    cache: dict[str, int]
    _next: int
    blob: list[tuple[int, str]]

    def __init__(self) -> None:
        self.cache = {}
        self._next = 0
        self.blob = []

    def add(self, name: str) -> int:
        if name in self.cache:
            return self.cache[name]
        else:
            off = self._next
            self.cache[name] = off
            self.blob.append((off, name))
            self._next += len(name) + 1  # +1 for null terminator
            return off

    def offset(self, name: str) -> int:
        return self.cache[name]

    def strings(self) -> Iterator[tuple[int, str]]:
        for s in self.blob:
            yield s


type Descriptors = StructDescriptor | FieldDescriptor | ArrayDescriptor


def sum_ntoks_with_cache() -> Callable[[CStruct | CType], int]:
    memo: dict[str, int] = {}

    def _weight(ctype: CType) -> int:
        if ctype.name == "char":
            return 1
        else:
            base = 1 if ctype.is_primitive else memo[ctype.name]
            for dim in reversed(ctype.dims):
                base = 1 + dim.max * base
            return base

    def _accumulate_ntoks(acc: int, field: Field) -> int:
        if isinstance(field.ctype, CType):
            return acc + _weight(field.ctype)
        else:
            acc += max(_weight(v.ctype) for v in field.ctype)
            return acc

    def sum_ntoks(s: CStruct | CType) -> int:
        if isinstance(s, CStruct):
            ntoks = reduce(_accumulate_ntoks, s.fields, 1 + len(s.fields))
            memo[s.ctype.name] = ntoks
            return ntoks
        else:
            return memo[s.name] if s.name in memo else _weight(s)

    return sum_ntoks


def add_array_with_cache() -> tuple[
    list[ArrayDescriptor], Callable[[ArrayDescriptor], Key]
]:
    memo: dict[tuple, Key] = {}
    arrays: list[ArrayDescriptor] = []

    def add_array(desc: ArrayDescriptor) -> Key:
        ident = (desc.kind, desc.max, desc.elem)
        if ident in memo:
            return memo[ident]
        else:
            memo[ident] = desc.key
            arrays.append(desc)
            return desc.key

    return arrays, add_array
