import io
from pathlib import Path
from typing import Any

import pytest
from jsmn_forge.lang.jsmn.render import RenderConfig, render
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "render"


@pytest.fixture(params=["jsmn", "jsmn-vla", "jsmn-every-type"])
def registry(request) -> Registry:
    spec = FIXTURES / f"{request.param}.openapi.yaml"
    resource = Resource.from_contents(yaml.load(spec), default_specification=DRAFT202012)
    registry: Registry[Any] = [resource] @ Registry()
    return registry


def test_render_snapshot(registry: Registry, snapshot) -> None:
    """Rendered C header matches snapshot."""
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    header = io.StringIO()
    source = io.StringIO()
    config = RenderConfig(
        resolver=registry.resolver(),
        output_header=header,
        output_source=source,
    )
    render(*specs, config=config)
    assert header.getvalue() == snapshot


def test_render_tables_snapshot(registry: Registry, snapshot) -> None:
    """Rendered C tables source matches snapshot."""
    specs = [r.contents for x in registry if (r := registry.get(x)) is not None]
    header = io.StringIO()
    source = io.StringIO()
    config = RenderConfig(
        resolver=registry.resolver(),
        output_header=header,
        output_source=source,
    )
    render(*specs, config=config)
    assert source.getvalue() == snapshot
