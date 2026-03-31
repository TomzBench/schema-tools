import pytest

from jsmn_tools.node import Ref

OPENAPI_SUFFIX = ".openapi.yaml"
ASYNCAPI_SUFFIX = ".asyncapi.yaml"


@pytest.mark.parametrize(
    "raw, suffix, expected",
    [
        # local — unchanged (suffix irrelevant)
        (
            "#/components/schemas/Foo",
            OPENAPI_SUFFIX,
            "#/components/schemas/Foo",
        ),
        # relative — collapse to fragment
        (
            "./auth.openapi.yaml#/components/schemas/Token",
            OPENAPI_SUFFIX,
            "#/components/schemas/Token",
        ),
        # relative, no fragment — pass through unchanged (authoring mistake)
        ("./auth.openapi.yaml", OPENAPI_SUFFIX, "./auth.openapi.yaml"),
        # scheme — rewrite to relative output file (openapi suffix)
        (
            "forge://sdk/common/v0#/components/schemas/Bar",
            OPENAPI_SUFFIX,
            "./sdk.openapi.yaml#/components/schemas/Bar",
        ),
        # scheme — rewrite to relative output file (asyncapi suffix)
        (
            "forge://sdk/common/v0#/components/schemas/Bar",
            ASYNCAPI_SUFFIX,
            "./sdk.asyncapi.yaml#/components/schemas/Bar",
        ),
        # scheme, no fragment
        ("forge://sdk/common/v0", OPENAPI_SUFFIX, "./sdk.openapi.yaml"),
        # scheme, no fragment (asyncapi)
        ("forge://sdk/common/v0", ASYNCAPI_SUFFIX, "./sdk.asyncapi.yaml"),
        # external URL — unchanged
        (
            "https://example.com/schema.json#/Foo",
            OPENAPI_SUFFIX,
            "https://example.com/schema.json#/Foo",
        ),
        # different scheme — unchanged
        (
            "other://mod/res/v1#/path",
            OPENAPI_SUFFIX,
            "other://mod/res/v1#/path",
        ),
    ],
)
def test_normalize(raw: str, suffix: str, expected: str) -> None:
    assert Ref(raw).normalize("forge", suffix) == expected


def test_is_local() -> None:
    assert Ref("#/foo").is_local
    assert not Ref("./file.yaml#/foo").is_local
    assert not Ref("forge://m/r/v0#/foo").is_local


def test_is_relative() -> None:
    assert Ref("./file.yaml#/foo").is_relative
    assert not Ref("#/foo").is_relative
    assert not Ref("forge://m/r/v0#/foo").is_relative
