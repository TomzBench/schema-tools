from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from jsmn_tools.spec import OPENAPI_3_1
from jsmn_tools.walk import prefixer

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "prefixer"


def _load() -> dict[str, Any]:
    return yaml.load(FIXTURES / "spec.openapi.yaml")


def test_prefixer_prepends_type_and_stamps_prefix():
    spec = _load()
    result = prefixer(spec, draft=OPENAPI_3_1, prefix="jsmn_")
    schemas = result["components"]["schemas"]

    assert schemas["about"]["x-jsmn-type"] == "jsmn_about"
    assert schemas["about"]["x-jsmn-prefix"] == "jsmn_"

    assert schemas["device"]["x-jsmn-type"] == "jsmn_device"
    assert schemas["device"]["x-jsmn-prefix"] == "jsmn_"

    assert schemas["device_list"]["x-jsmn-type"] == "jsmn_device_list"
    assert schemas["device_list"]["x-jsmn-prefix"] == "jsmn_"


def test_prefixer_idempotent():
    spec = _load()
    once = prefixer(spec, draft=OPENAPI_3_1, prefix="jsmn_")
    twice = prefixer(once, draft=OPENAPI_3_1, prefix="jsmn_")
    for name in ("about", "device", "device_list"):
        assert (
            once["components"]["schemas"][name]["x-jsmn-type"]
            == twice["components"]["schemas"][name]["x-jsmn-type"]
        )


def test_prefixer_empty_prefix_is_noop():
    spec = _load()
    result = prefixer(spec, draft=OPENAPI_3_1, prefix="")
    schemas = result["components"]["schemas"]
    assert schemas["about"]["x-jsmn-type"] == "about"
    assert "x-jsmn-prefix" not in schemas["about"]


def test_prefixer_preserves_refs():
    spec = _load()
    result = prefixer(spec, draft=OPENAPI_3_1, prefix="jsmn_")
    schemas = result["components"]["schemas"]
    assert schemas["device"]["properties"]["info"]["$ref"] == (
        "#/components/schemas/about"
    )
    assert schemas["device_list"]["items"]["$ref"] == (
        "#/components/schemas/device"
    )


def test_prefixer_does_not_mutate_input():
    spec = _load()
    original = spec["components"]["schemas"]["about"]["x-jsmn-type"]
    prefixer(spec, draft=OPENAPI_3_1, prefix="jsmn_")
    assert spec["components"]["schemas"]["about"]["x-jsmn-type"] == original
