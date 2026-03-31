# AsyncAPI walk tests cover traversal only. Flatten code branches are already
# exercised by the OpenAPI flatten tests — the draft tree is an input to
# flatten, not a code path within it. The asymmetry with OpenAPI tests is
# intentional.

from pathlib import Path
from typing import Any

from jsmn_tools.spec import ASYNCAPI_3_0
from jsmn_tools.walk import walk
from ruamel.yaml import YAML

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "walk"


def load(name: str) -> Any:
    return yaml.load(FIXTURES / name)


def test_walk_channels_yields_schema_enter() -> None:
    """Message payload and headers are walked as schema_enter."""
    steps = list(walk(load("asyncapi_channels.yaml"), draft=ASYNCAPI_3_0))
    kinds = [s.kind for s in steps]
    assert "channel" in kinds
    assert "message" in kinds
    assert "schema_enter" in kinds


def test_walk_components_schemas() -> None:
    """components/schemas entries are walked as schema_enter."""
    steps = list(walk(load("asyncapi_components.yaml"), draft=ASYNCAPI_3_0))
    schema_enters = [
        s for s in steps
        if s.kind == "schema_enter"
        and isinstance(s.value, dict)
        and s.value.get("type") == "object"
    ]
    assert len(schema_enters) > 0


def test_walk_message_headers() -> None:
    """Message headers are walked as schema_enter."""
    steps = list(walk(load("asyncapi_channels.yaml"), draft=ASYNCAPI_3_0))
    header_schemas = [
        s for s in steps
        if s.kind == "schema_enter"
        and isinstance(s.value, dict)
        and "correlationId" in s.value.get("properties", {})
    ]
    assert len(header_schemas) == 1


def test_walk_message_trait_headers() -> None:
    """Message trait headers are walked as schema_enter."""
    steps = list(walk(load("asyncapi_components.yaml"), draft=ASYNCAPI_3_0))
    trait_headers = [
        s for s in steps
        if s.kind == "schema_enter"
        and isinstance(s.value, dict)
        and "correlationId" in s.value.get("properties", {})
    ]
    assert len(trait_headers) == 1


def test_walk_server_variables() -> None:
    """Server variables are traversed with correct node kinds."""
    steps = list(walk(load("asyncapi_channels.yaml"), draft=ASYNCAPI_3_0))
    kinds = [s.kind for s in steps]
    assert "server" in kinds
    assert "server_var" in kinds


def test_walk_parameters_not_schema() -> None:
    """Channel parameters are obj_parameter, not schema_enter."""
    steps = list(walk(load("asyncapi_channels.yaml"), draft=ASYNCAPI_3_0))
    param_steps = [s for s in steps if s.kind == "parameter"]
    assert len(param_steps) > 0
    # Parameters should not produce schema_enter children
    for ps in param_steps:
        assert ps.kind != "schema_enter"


def test_walk_multi_spec() -> None:
    """Variadic walk yields steps from every spec."""
    a = load("asyncapi_channels.yaml")
    b = load("asyncapi_components.yaml")
    combined = list(walk(a, b, draft=ASYNCAPI_3_0))
    solo_a = list(walk(a, draft=ASYNCAPI_3_0))
    solo_b = list(walk(b, draft=ASYNCAPI_3_0))
    assert len(combined) == len(solo_a) + len(solo_b)
