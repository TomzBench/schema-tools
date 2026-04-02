from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from jsmn_tools.lang.jsmn.prepare import CodegenBundle, codegen
from jsmn_tools.lang.jsmn.render import Renderer

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "render"


@pytest.fixture(params=["jsmn", "jsmn-vla", "jsmn-every-type"])
def compiled(request) -> CodegenBundle:
    spec = FIXTURES / f"{request.param}.openapi.yaml"
    resource = Resource.from_contents(
        yaml.load(spec), default_specification=DRAFT202012
    )
    registry: Registry[Any] = [resource] @ Registry()
    return codegen(registry)


def test_renderer_jsmn_generated_decl(compiled: CodegenBundle, snapshot) -> None:
    """Render components"""
    renderer = Renderer(compiled)
    tpl = "{% include 'jsmn_generated.h' %}"
    assert renderer.render(tpl) == snapshot


def test_renderer_jsmn_generated_impl(compiled: CodegenBundle, snapshot) -> None:
    """Render components"""
    renderer = Renderer(compiled)
    tpl = "{% include 'jsmn_generated.c' %}"
    assert renderer.render(tpl) == snapshot


def test_renderer_runtime_snapshot(snapshot) -> None:
    """Runtime files are loadable via prefix loader with includes stripped."""
    renderer = Renderer(CodegenBundle.empty())
    tpl = dedent("""\
        {% include 'jsmn.h' %}
        {% include 'runtime.h' %}
        {% include 'runtime.c' %}
        """)
    assert renderer.render(tpl) == snapshot


def test_renderer_hoist_includes(snapshot) -> None:
    """System includes are deduplicated and hoisted to the top."""
    renderer = Renderer(CodegenBundle.empty())
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
