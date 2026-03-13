import pytest
from jsmn_forge.lang.jsmn import CType, Dim, Field, Variant, field, mangle


@pytest.mark.parametrize(
    "c_type,expected",
    [
        ("uint8_t", "u8"),
        ("int8_t", "i8"),
        ("uint16_t", "u16"),
        ("int16_t", "i16"),
        ("uint32_t", "u32"),
        ("int32_t", "i32"),
        ("uint64_t", "u64"),
        ("int64_t", "i64"),
        ("bool", "bool"),
    ],
)
def test_mangle_primitives(c_type: str, expected: str) -> None:
    assert mangle(CType(c_type)) == expected


def test_mangle_object() -> None:
    """Struct names pass through; underscore in name triggers __ separator."""
    assert mangle(CType("thing_nested")) == "thing_nested"


def test_mangle_fixed_dims() -> None:
    """Consecutive fixed dims group as __d{d1}x{d2}x..."""
    dims = (Dim(3, 3), Dim(4, 4), Dim(9, 9))
    assert mangle(CType("uint8_t", dims)) == "u8__d3x4x9"


def test_mangle_vla() -> None:
    assert mangle(CType("uint32_t", (Dim(0, 3),))) == "vla__u32__n3"


def test_mangle_nested_vla() -> None:
    """Each VLA wrap uses __ boundary."""
    dims = (Dim(0, 4), Dim(0, 3))
    assert mangle(CType("uint32_t", dims)) == "vla__vla__u32__n3__n4"


def test_mangle_vla_of_fixed() -> None:
    """Fixed dims flushed before VLA wrap; mixed partition."""
    dims = (Dim(0, 4), Dim(3, 3))
    assert mangle(CType("uint32_t", dims)) == "vla__u32__d3__n4"


def test_field_required_primitive() -> None:
    assert field(Field("flag", CType("bool"), True)) == "bool flag"


def test_field_required_primitive_dims() -> None:
    f = Field("name", CType("uint8_t", (Dim(32, 32),)), True)
    assert field(f) == "uint8_t name[32]"


def test_field_required_object() -> None:
    assert field(Field("nested", CType("thing"), True)) == "struct thing nested"


def test_field_required_vla() -> None:
    f = Field("nums", CType("uint32_t", (Dim(0, 3),)), True)
    assert field(f) == "struct vla__u32__n3 nums"


def test_field_optional() -> None:
    f = Field("count", CType("uint32_t"), False)
    assert field(f) == "struct optional__u32 count"


# --- Union mangling ---


def test_mangle_union1() -> None:
    """Degenerate single-variant union."""
    assert mangle((Variant("foo", CType("foo")),)) == "union1__foo"


def test_mangle_union3_sorted() -> None:
    """Variants are sorted by mangled name; primitives are shortened."""
    variants = (
        Variant("foo", CType("foo")),
        Variant("bar", CType("bar")),
        Variant("count", CType("uint32_t")),
    )
    assert mangle(variants) == "union3__bar__foo__u32"


def test_mangle_union_with_vla_variant() -> None:
    """VLA variant is self-delimiting inside the union name."""
    variants = (
        Variant("nums", CType("uint32_t", (Dim(0, 3),))),
        Variant("flag", CType("bool")),
    )
    assert mangle(variants) == "union2__bool__vla__u32__n3"


def test_mangle_union_with_fixed_dim_variant() -> None:
    """Fixed-dim variant inside union."""
    variants = (
        Variant("name", CType("uint8_t", (Dim(32, 32),))),
        Variant("flag", CType("bool")),
    )
    assert mangle(variants) == "union2__bool__u8__d32"


def test_field_union_required() -> None:
    """Required union field uses 'union' qualifier."""
    variants = (Variant("bar", CType("bar")), Variant("foo", CType("foo")))
    f = Field("status", variants, True)
    assert field(f) == "union union2__bar__foo status"


def test_field_union_optional() -> None:
    """Optional union wraps in struct optional__, not union optional__."""
    variants = (Variant("bar", CType("bar")), Variant("foo", CType("foo")))
    f = Field("status", variants, False)
    assert field(f) == "struct optional__union2__bar__foo status"
