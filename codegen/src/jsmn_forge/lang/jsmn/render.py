from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TextIO

from jinja2 import Environment, PackageLoader

from .descriptor import (
    ArrayDescriptor,
    ArrayKind,
    Descriptors,
    FieldDescriptor,
    Key,
    Strings,
    StructDescriptor,
    Table,
    add_array_with_cache,
    sum_ntoks_with_cache,
)
from .filters import filters, mangle
from .flatten import flatten_with_resolver

if TYPE_CHECKING:
    from collections.abc import Sequence

    from jsmn_forge.node import Location
    from referencing._core import Resolver
from .ir import (
    CDecl,
    CStruct,
    CType,
    CUnion,
    Dim,
    Field,
    FixedDims,
    Variant,
)


def _make_optional(inner: CType, loc: Location) -> CStruct:
    ctype = CType(inner.mangle(optional=True))
    return CStruct(
        ctype,
        loc,
        [
            Field("present", CType("bool")),
            Field("maybe", (Variant("value", inner),)),
        ],
    )


def _make_maybe(inner: CType, loc: Location) -> CUnion:
    variants = (Variant("value", inner),)
    ctype = CType(mangle(variants))
    return CUnion(ctype, loc, [Variant("value", inner)])


def _make_vla(ctype: CType, loc: Location) -> CStruct:
    cap = ctype.dims[0].max
    rest = ctype.dims[1:]
    return CStruct(
        CType(ctype.mangle()),
        loc,
        [
            Field("len", CType("uint32_t")),
            Field("_pad", CType("uint8_t", (Dim(4, 4),))),
            Field("items", CType(ctype.name, (Dim(cap, cap), *rest))),
        ],
    )


def sort_and_extend_decls(decls: dict[CType, CDecl]) -> list[CDecl]:
    cache: set[CType] = set()
    ret: list[CDecl] = []

    def walker(curr: CDecl) -> None:
        if curr.ctype in cache:
            return
        if isinstance(curr, CStruct):
            for prop in curr.fields:
                if isinstance(prop.ctype, CType):
                    prop_loc = curr.loc.push(prop.name)
                    if not prop.required:
                        walker(_make_maybe(prop.ctype, prop_loc))
                        walker(_make_optional(prop.ctype, prop_loc))
                    for group, spec in prop.ctype.dim_walk():
                        if isinstance(group, FixedDims):
                            continue
                        walker(_make_vla(spec, prop_loc))
                    if prop.ctype in decls:
                        walker(decls[prop.ctype])
                else:
                    for v in prop.ctype:
                        if v.ctype in decls:
                            walker(decls[v.ctype])
            cache.add(curr.ctype)
            ret.append(curr)
        elif isinstance(curr, CUnion):
            # TODO this is minimally required for optional types. oneof support
            #      will need proper walker
            cache.add(curr.ctype)
            ret.append(curr)
        else:
            raise NotImplementedError

    for decl in decls.values():
        walker(decl)

    return ret


def build_tables(
    ordered: Sequence[CDecl],
) -> tuple[Strings, dict[Key, Descriptors]]:
    structs: list[StructDescriptor] = []
    fields: list[FieldDescriptor] = []
    arrays, add_array = add_array_with_cache()
    sum_ntoks = sum_ntoks_with_cache()
    strings = Strings()

    def resolve_array(ctype: CType, loc: Location) -> Key:
        """Walk dims inner-to-outer, creating/reusing array descriptors."""
        ref: Key | CType = CType(ctype.name)  # bare leaf
        for group, spec in ctype.dim_walk():
            kind = ArrayKind.from_group(group)
            entries = (
                [(ctype, dim.max) for dim in reversed(group.dims)]
                if isinstance(group, FixedDims)
                else [(spec, group.max)]
            )
            for ct, mx in entries:
                arr = ArrayDescriptor(
                    key=Key(Table.ARRAY, len(arrays)),
                    loc=loc,
                    ntoks=0,
                    ctype=ct,
                    kind=kind,
                    max=mx,
                    elem=ref,
                )
                ref = add_array(arr)
        assert isinstance(ref, Key)
        return ref

    for d in ordered:
        if isinstance(d, CStruct):
            struct_key = Key(Table.STRUCT, len(structs))
            s = StructDescriptor(
                key=struct_key,
                loc=d.loc,
                ntoks=sum_ntoks(d),
                ctype=d.ctype,
                nfields=len(d.fields),
                field0=len(fields),
            )
            structs.append(s)
            for f in d.fields:
                if not isinstance(f.ctype, CType):
                    raise NotImplementedError("unions not implemented yet")
                type_ref: Key | CType = f.ctype
                if f.ctype.dims:
                    type_ref = resolve_array(f.ctype, d.loc)
                desc = FieldDescriptor(
                    key=Key(Table.FIELD, len(fields)),
                    loc=d.loc,
                    ntoks=sum_ntoks(f.ctype),
                    ctype=f.ctype,
                    name=f.name,
                    name_offset=strings.add(f.name),
                    parent=struct_key,
                    optional=not f.required,
                    type_ref=type_ref,
                )
                fields.append(desc)
    table = {d.key: d for d in [*structs, *fields, *arrays]}
    return strings, table


@dataclass
class RenderConfig:
    resolver: Resolver
    output_header: TextIO
    output_source: TextIO
    guard: str = "__JSMN_FORGE_H__"
    header_name: str = "jsmn_forge.h"


def render(*specs: Any, config: RenderConfig) -> None:
    result = flatten_with_resolver(*specs, resolver=config.resolver)
    if result.errors:
        raise ValueError(result.errors)
    decls = sort_and_extend_decls(result.decls)

    # Build tables from user-defined structs
    def is_user_struct(d: CDecl) -> bool:
        return isinstance(d, CStruct) and d.ctype in result.decls

    user_ordered = [d for d in decls if is_user_struct(d)]

    blob, table = build_tables(user_ordered)

    env = Environment(
        loader=PackageLoader("jsmn_forge", "lang/jsmn/templates"),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    for name, fn in filters(table=table).items():
        env.filters[name] = fn
    env.tests["struct_decl"] = lambda val: isinstance(val, CStruct)
    env.tests["union_decl"] = lambda val: isinstance(val, CUnion)

    # Render header
    template = env.get_template("header.h.jinja2")
    config.output_header.write(template.render(decls=decls, guard=config.guard))

    # Render tables source
    descriptors = sorted(table.values(), key=lambda d: d.key.pos)
    tables_template = env.get_template("tables.c.jinja2")
    config.output_source.write(
        tables_template.render(
            header=config.header_name,
            blob=blob,
            descriptors=descriptors,
        )
    )
