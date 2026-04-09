from pathlib import Path
from textwrap import dedent

import pytest
from jinja2 import Environment
from referencing import Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from referencing import Registry

from jsmn_tools.jsmn.prepare import bundle_codegen, extend_codegen
from jsmn_tools.jsmn.render import hoist_includes

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "render"


@pytest.fixture(params=["jsmn", "jsmn-vla", "jsmn-every-type"])
def env(request) -> Environment:
    spec = FIXTURES / f"{request.param}.openapi.yaml"
    resource = Resource.from_contents(
        yaml.load(spec), default_specification=DRAFT202012
    )
    registry = [resource] @ Registry()
    resolver, bundle = bundle_codegen(registry)
    jinja_env = Environment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    extend_codegen(jinja_env, bundle, resolver=resolver, prefix="jsmn_")
    return jinja_env


@pytest.fixture()
def empty_env() -> Environment:
    resolver, bundle = bundle_codegen(Registry())
    jinja_env = Environment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    extend_codegen(jinja_env, bundle, resolver=resolver, prefix="jsmn_")
    return jinja_env


def test_renderer_jsmn_generated_decl(env: Environment, snapshot) -> None:
    """Render components"""
    tpl = "{% include 'jsmn_generated.h' %}"
    assert env.from_string(tpl).render() == snapshot


def test_renderer_jsmn_generated_impl(env: Environment, snapshot) -> None:
    """Render components"""
    tpl = "{% include 'jsmn_generated.c' %}"
    assert env.from_string(tpl).render() == snapshot


def test_renderer_runtime_snapshot(empty_env: Environment, snapshot) -> None:
    """Runtime files are loadable via prefix loader with includes stripped."""
    tpl = dedent("""\
        {% include 'jsmn.h' %}
        {% include 'runtime.h' %}
        {% include 'runtime.c' %}
        """)
    assert empty_env.from_string(tpl).render() == snapshot


def test_renderer_hoist_includes(empty_env: Environment, snapshot) -> None:
    """System includes are deduplicated and hoisted to the top."""
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
    result = hoist_includes(empty_env.from_string(tpl).render())
    assert result == snapshot
