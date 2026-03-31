import pytest
from jsmn_tools.lang.jsmn import (
    CType,
    Dim,
    Variant,
    mangle,
    resolve_ctype,
)


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


# --- resolve_ctype tests ---


def test_resolve_scalar_primitive() -> None:
    assert resolve_ctype(CType("uint32_t")) == CType("uint32_t")


def test_resolve_fixed_dims() -> None:
    ct = CType("uint8_t", (Dim(32, 32),))
    assert resolve_ctype(ct) == ct


def test_resolve_string_dim() -> None:
    ct = CType("char", (Dim(33, 33),))
    assert resolve_ctype(ct) == ct


def test_resolve_object_ref() -> None:
    assert resolve_ctype(CType("child")) == CType("child")


def test_resolve_single_vla() -> None:
    assert resolve_ctype(CType("uint32_t", (Dim(0, 5),))) == CType("vla__u32__n5")


def test_resolve_nested_vla() -> None:
    dims = (Dim(0, 5), Dim(0, 4), Dim(0, 3))
    assert resolve_ctype(CType("uint32_t", dims)) == CType(
        "vla__vla__vla__u32__n3__n4__n5"
    )


def test_resolve_leading_fixed_vla() -> None:
    """Leading fixed dims stay as dims; inner VLAs collapse into name."""
    dims = (Dim(5, 5), Dim(0, 4), Dim(0, 3))
    assert resolve_ctype(CType("uint32_t", dims)) == CType(
        "vla__vla__u32__n3__n4", (Dim(5, 5),)
    )


def test_resolve_multi_fixed_then_vla() -> None:
    dims = (Dim(5, 5), Dim(4, 4), Dim(0, 3))
    assert resolve_ctype(CType("uint32_t", dims)) == CType(
        "vla__u32__n3", (Dim(5, 5), Dim(4, 4))
    )


def test_resolve_all_fixed() -> None:
    dims = (Dim(5, 5), Dim(4, 4), Dim(3, 3))
    ct = CType("uint32_t", dims)
    assert resolve_ctype(ct) == ct


def test_resolve_vla_of_string() -> None:
    dims = (Dim(0, 4), Dim(17, 17))
    assert resolve_ctype(CType("char", dims)) == CType("vla__char__d17__n4")
