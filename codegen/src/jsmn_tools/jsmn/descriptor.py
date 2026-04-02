# id -> 2 bit tag: xx1 primitive (bits[15:1] = scalar id)
#                  000 struct    (bits[15:2] idx to struct[])
#                  100 array     (bits[15:2] idx to array[])
# NOTE current optional handling "dots into" the offset of assumed wrapper types
# confusing but works. ie: offsetof(struct parent, count) is a pointer to "present" field
# more natural to possibly just store idx of wrapper types into the structs, but decoder has
# to set the "present" field. so perhaps parent should manage the present field and recurse
# into values... (evaluate when implementing runtime.c)
# nameblob[]
# jt_array[]   comment, kind, min, max, elem_size, desc_idx
# jt_field[]   comment, off_name, off_value, off_present, desc_idx
# jt_struct[]  comment, nfields, size, ntoks, field0
# JT_{{struct.name | upper}}_IDX {{idx}}
# JT_{{struct.name | upper}}_TOK {{idx}}
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

from jsmn_tools.node import Location

from .ir import CArray, CStruct, CType, CUnion, Dim, Field, FixedDims, StringDim
from .mangle import mangle


class EscapeMode(Enum):
    """Char multiplier for worst-case encode buffer calculation."""

    NONE = 1  # pass-through, no escaping
    BASIC = 2  # escape " \ and control chars
    UNICODE = 6  # \uXXXX for everything non-ASCII


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
    encode_len: int
    ctype: CType


@dataclass
class StructDescriptor(Descriptor):
    """All context for rendering a struct entry in a struct jt_struct"""

    """Number of fields"""
    nfields: int
    """Position of first field in fields table"""
    field0: int


@dataclass
class FieldDescriptor(Descriptor):
    """All context for rendering a field entry in a struct jt_field"""

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
    """All context for rendering an array entry in a struct jt_array"""

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
        base = 1 if ctype.is_primitive else memo[ctype.name]
        if ctype.dims:
            for dim in reversed(ctype.dims):
                base = 1 + dim.max * base
            memo[mangle(ctype)] = base
            return base
        else:
            return base

    def _accumulate_ntoks(acc: int, field: Field) -> int:
        if isinstance(field.ctype, CType):
            return acc + _weight(field.ctype)
        else:
            acc += max(_weight(v.ctype) for v in field.ctype)
            return acc

    def sum_ntoks(s: CStruct | CArray | CUnion | CType) -> int:
        if isinstance(s, CStruct):
            ntoks = reduce(_accumulate_ntoks, s.fields, 1 + len(s.fields))
            memo[s.ctype.name] = ntoks
            return ntoks
        elif isinstance(s, CArray):
            ntoks = 1 + sum_ntoks(s.elem) * s.max  # [ ] tok + N * elem
            memo[s.ctype.name] = ntoks
            return ntoks
        elif isinstance(s, CUnion):
            ntoks = max(sum_ntoks(v.ctype) for v in s.variants)
            memo[s.ctype.name] = ntoks
            return ntoks
        else:
            return _weight(s)

    return sum_ntoks


def sum_encode_len_with_cache(
    escape: EscapeMode = EscapeMode.NONE,
) -> Callable[[CStruct | CType], int]:
    memo: dict[str, int] = {}

    # Worst-case JSON text length per primitive value
    # fmt: off
    _PRIMITIVE_LEN: dict[str, int] = {
        "bool": 5,            # false
        "char": escape.value, # See: EscapeMode
        "uint8_t": 3,         # 255
        "int8_t": 4,          # -128
        "uint16_t": 5,        # 65535
        "int16_t": 6,         # -32768
        "uint32_t": 10,       # 4294967295
        "int32_t": 11,        # -2147483648
        "uint64_t": 20,       # 18446744073709551615
        "int64_t": 20,        # -9223372036854775808
        "float": 13,          # -%g worst case (C99+)
        "double": 24,         # -%.17g worst case (C99+)
    }
    # fmt: on

    def _weight(ctype: CType) -> int:
        if ctype.is_string:
            # "content" = 2 quotes + (buf - 1) * char_weight
            # buf includes null terminator, so max content = buf - 1
            base = 2 + (ctype.dims[-1].max - 1) * _PRIMITIVE_LEN["char"]
            dims = ctype.dims[:-1]
        elif ctype.is_primitive:
            base = _PRIMITIVE_LEN[ctype.name]
            dims = ctype.dims
        else:
            base = memo[ctype.name]
            dims = ctype.dims
        if dims:
            # [elem,elem,...] = 2 + N*elem + (N-1) commas
            for dim in reversed(dims):
                base = 2 + dim.max * base + max(0, dim.max - 1)
            memo[mangle(ctype)] = base
            return base
        else:
            return base

    def _accumulate(acc: int, field: Field) -> int:
        # "name":val = len(name) + 2 quotes + 1 colon + val
        if isinstance(field.ctype, CType):
            return acc + len(field.name) + 3 + _weight(field.ctype)
        else:
            acc += (
                len(field.name) + 3 + max(_weight(v.ctype) for v in field.ctype)
            )
            return acc

    def sum_encode_len(s: CStruct | CArray | CUnion | CType) -> int:
        if isinstance(s, CStruct):
            # {field,field,...} = 2 braces + (N-1) commas
            commas = max(0, len(s.fields) - 1)
            nbytes = reduce(_accumulate, s.fields, 2 + commas)
            memo[s.ctype.name] = nbytes
            return nbytes
        elif isinstance(s, CArray):
            # [elem,elem,...] = 2 brackets + N*elem + (N-1) commas
            nbytes = 2 + s.max * sum_encode_len(s.elem) + max(0, s.max - 1)
            memo[s.ctype.name] = nbytes
            return nbytes
        elif isinstance(s, CUnion):
            nbytes = max(sum_encode_len(v.ctype) for v in s.variants)
            memo[s.ctype.name] = nbytes
            return nbytes
        else:
            return _weight(s)

    return sum_encode_len


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
