import pytest
from jsmn_forge.node import Ref


@pytest.mark.parametrize(
    "raw, expected",
    [
        # local — unchanged
        ("#/components/schemas/Foo", "#/components/schemas/Foo"),
        # relative — collapse to fragment
        (
            "./auth.openapi.yaml#/components/schemas/Token",
            "#/components/schemas/Token",
        ),
        # relative, no fragment — pass through unchanged (authoring mistake)
        ("./auth.openapi.yaml", "./auth.openapi.yaml"),
        # scheme — rewrite to relative output file
        (
            "forge://sdk/common/v0#/components/schemas/Bar",
            "./sdk.openapi.yaml#/components/schemas/Bar",
        ),
        # scheme, no fragment
        ("forge://sdk/common/v0", "./sdk.openapi.yaml"),
        # external URL — unchanged
        (
            "https://example.com/schema.json#/Foo",
            "https://example.com/schema.json#/Foo",
        ),
        # different scheme — unchanged
        ("other://mod/res/v1#/path", "other://mod/res/v1#/path"),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert Ref(raw).normalize("forge") == expected


def test_is_local() -> None:
    assert Ref("#/foo").is_local
    assert not Ref("./file.yaml#/foo").is_local
    assert not Ref("forge://m/r/v0#/foo").is_local


def test_is_relative() -> None:
    assert Ref("./file.yaml#/foo").is_relative
    assert not Ref("#/foo").is_relative
    assert not Ref("forge://m/r/v0#/foo").is_relative
