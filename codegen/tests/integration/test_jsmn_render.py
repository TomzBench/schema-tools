from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest
from jsmn_forge.lang.jsmn.flatten import flatten_with_resolver
from jsmn_forge.lang.jsmn.render import Renderer
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "render"


@pytest.fixture(params=["jsmn", "jsmn-vla", "jsmn-every-type"])
def registry(request) -> Registry:
    spec = FIXTURES / f"{request.param}.openapi.yaml"
    resource = Resource.from_contents(
        yaml.load(spec), default_specification=DRAFT202012
    )
    registry: Registry[Any] = [resource] @ Registry()
    return registry


def test_renderer_schema_generated_decl(registry: Registry, snapshot) -> None:
    """Render components"""
    specs = [r.contents for r in registry.values()]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    renderer = Renderer(result.decls)
    tpl = "{% include 'schema_generated.h' %}"
    assert renderer.render(tpl) == snapshot


def test_renderer_schema_generated_impl(registry: Registry, snapshot) -> None:
    """Render components"""
    specs = [r.contents for r in registry.values()]
    result = flatten_with_resolver(*specs, resolver=registry.resolver())
    renderer = Renderer(result.decls)
    tpl = "{% include 'schema_generated.c' %}"
    assert renderer.render(tpl) == snapshot


def test_renderer_runtime_snapshot(snapshot) -> None:
    """Runtime files are loadable via prefix loader with includes stripped."""
    renderer = Renderer({})
    tpl = dedent("""\
        {% include 'jsmn.h' %}
        {% include 'runtime.h' %}
        {% include 'runtime.c' %}
        """)
    assert renderer.render(tpl) == snapshot


def test_renderer_hoist_includes(snapshot) -> None:
    """System includes are deduplicated and hoisted to the top."""
    renderer = Renderer({})
    tpl = dedent("""\
        #include <stdint.h>
        #include <stdbool.h>
        void foo(void);
        #include <stdint.h>
        #include <string.h>
        void bar(void);
        #include <stdbool.h>
        #include <stddef.h>
        """)
    assert renderer.render(tpl, hoist_includes=True) == snapshot
