from pathlib import Path
from typing import Any

import pytest
from jsmn_forge.spec import OPENAPI_3_1
from jsmn_forge.walk import join
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


@pytest.fixture
def walk_data() -> dict[str, Any]:
    walk = Path(__file__).parent.parent.absolute() / "fixtures" / "join"
    return {file.stem: file.absolute() for file in walk.iterdir()}


def test_normalize_refs(walk_data: dict[str, Any]) -> None:
    """$ref values are rewritten in schema-aware contexts but left
    untouched inside data traps (default, x-*)."""
    result = join(walk_data["refs"], scheme="forge", draft=OPENAPI_3_1)
    assert result.conflicts == []
    schemas = result.value["components"]["schemas"]

    # Direct $ref — local, unchanged
    assert schemas["direct"]["$ref"] == "#/components/schemas/target"

    # Properties: local unchanged, external rewritten
    props = schemas["in_properties"]["properties"]
    assert props["local"]["$ref"] == "#/components/schemas/target"
    assert (
        props["external"]["$ref"]
        == "./sdk.openapi.yaml#/components/schemas/Foo"
    )

    # allOf: scheme ref rewritten, relative ref collapsed to fragment
    allOf = schemas["in_properties"]["allOf"]
    refs = sorted(item["$ref"] for item in allOf)
    assert "#/components/schemas/Baz" in refs
    assert "./sdk.openapi.yaml#/components/schemas/Bar" in refs

    # $ref with sibling keys — ref rewritten, siblings preserved
    assert schemas["with_siblings"]["$ref"] == "#/components/schemas/target"
    assert schemas["with_siblings"]["description"] == "has sibling keys"

    # Data traps — $ref is just data, NOT rewritten
    traps = schemas["data_traps"]
    assert traps["default"]["$ref"] == "#/not_a_real_ref"
    assert traps["x-meta"]["$ref"] == "forge://sdk/common/v0#/not_a_real_ref"
