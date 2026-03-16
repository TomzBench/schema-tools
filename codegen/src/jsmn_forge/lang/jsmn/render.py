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
from .filters import filters, tests
from .flatten import flatten_with_resolver
from .ir import CDecl, CStruct, CType, CUnion, Field, FixedDims
from .mangle import dim_walk, make_maybe, make_optional, make_vla, mangle

if TYPE_CHECKING:
    from collections.abc import Sequence

    from jsmn_forge.node import Location
    from referencing._core import Resolver


def resolve_ctype(ctype: CType, optional: bool = False) -> CType:
    """Collapse VLA dims into wrapper names, keep leading fixed dims."""
    inner = CType(ctype.name)
    for group in ctype.dim_groups():
        if isinstance(group, FixedDims):
            inner = CType(inner.name, group.dims)
        else:
            spec = CType(inner.name, (group, *inner.dims))
            inner = CType(mangle(spec))
    if optional:
        return CType(mangle(inner, optional=True))
    else:
        return inner


def sort_decls(decls: dict[CType, CDecl]) -> list[CDecl]:
    """Dependency-order user-defined decls (no synthetic wrappers)."""
    cache: set[CType] = set()
    ret: list[CDecl] = []

    def walker(curr: CDecl) -> None:
        if curr.ctype in cache:
            return
        if isinstance(curr, CStruct):
            for prop in curr.fields:
                if isinstance(prop.ctype, CType):
                    if prop.ctype in decls:
                        walker(decls[prop.ctype])
                else:
                    for v in prop.ctype:
                        if v.ctype in decls:
                            walker(decls[v.ctype])
            cache.add(curr.ctype)
            ret.append(curr)
        else:
            raise NotImplementedError

    for decl in decls.values():
        walker(decl)
    return ret


def extend_decls(ordered: list[CDecl]) -> list[CDecl]:
    """Create synthetic wrappers and resolve field CTypes in one pass."""
    cache: set[CType] = set()
    ret: list[CDecl] = []

    def emit(d: CDecl) -> None:
        if d.ctype not in cache:
            cache.add(d.ctype)
            ret.append(d)

    for d in ordered:
        if isinstance(d, CStruct):
            fields: list[Field] = []
            for f in d.fields:
                if not isinstance(f.ctype, CType):
                    if not f.required:
                        resolved = CType(mangle(f.ctype, optional=True))
                        fields.append(Field(f.name, resolved, required=True))
                    else:
                        fields.append(f)
                else:
                    prop_loc = d.loc.push(f.name)
                    resolved = resolve_ctype(f.ctype)
                    for group, spec in dim_walk(f.ctype):
                        if not isinstance(group, FixedDims):
                            emit(make_vla(spec, prop_loc))
                    if not f.required:
                        emit(make_maybe(resolved, prop_loc))
                        emit(make_optional(resolved, prop_loc))
                        resolved = resolve_ctype(f.ctype, optional=True)
                        fields.append(Field(f.name, resolved, required=True))
                    else:
                        fields.append(Field(f.name, resolved, f.required))
            emit(CStruct(d.ctype, d.loc, fields))
        elif isinstance(d, CUnion):
            emit(d)
        else:
            raise NotImplementedError
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
        for group, spec in dim_walk(ctype):
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
                    ctype=resolve_ctype(ct),
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
                    ctype=resolve_ctype(f.ctype, optional=not f.required),
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
    prefix: str = "schema_"


def render(*specs: Any, config: RenderConfig) -> None:
    result = flatten_with_resolver(*specs, resolver=config.resolver)
    if result.errors:
        raise ValueError(result.errors)

    sorted_user = sort_decls(result.decls)
    blob, table = build_tables(sorted_user)
    decls = extend_decls(sorted_user)

    env = Environment(
        loader=PackageLoader("jsmn_forge", "lang/jsmn/templates"),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    for name, fn in tests(sorted_user).items():
        env.tests[name] = fn
    for name, fn in filters(table=table, decls=decls).items():
        env.filters[name] = fn

    # Render header
    template = env.get_template("header.h.jinja2")

    oh = template.render(
        decls=decls,
        guard=config.guard,
        prefix=config.prefix,
    )
    config.output_header.write(oh)

    # Render tables source
    descriptors = sorted(table.values(), key=lambda d: d.key.pos)
    tables_template = env.get_template("tables.c.jinja2")
    os = tables_template.render(
        header=config.header_name,
        blob=blob,
        descriptors=descriptors,
    )
    config.output_source.write(os)
