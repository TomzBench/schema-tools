from pathlib import Path
from textwrap import dedent

import pytest
from jinja2 import Environment as JinjaEnvironment
from referencing import Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from jsmn_tools.jsmn import Environment
from jsmn_tools.jsmn.render import hoist_includes

yaml = YAML(typ="safe")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "render"


@pytest.fixture(params=["jsmn", "jsmn-vla", "jsmn-every-type"])
def env(request) -> JinjaEnvironment:
    spec = FIXTURES / f"{request.param}.openapi.yaml"
    resource = Resource.from_contents(
        yaml.load(spec), default_specification=DRAFT202012
    )
    jsmn = Environment.from_specifications(resource)
    jinja_env = JinjaEnvironment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    jsmn.extend(jinja_env, prefix="jsmn_")
    return jinja_env


@pytest.fixture()
def empty_env() -> JinjaEnvironment:
    jsmn = Environment.empty()
    jinja_env = JinjaEnvironment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    jsmn.extend(jinja_env, prefix="jsmn_")
    return jinja_env


def test_renderer_jsmn_generated_decl(env: JinjaEnvironment, snapshot) -> None:
    """Render components"""
    tpl = "{% include 'jsmn_generated.h' %}"
    assert env.from_string(tpl).render() == snapshot


def test_renderer_jsmn_generated_impl(env: JinjaEnvironment, snapshot) -> None:
    """Render components"""
    tpl = "{% include 'jsmn_generated.c' %}"
    assert env.from_string(tpl).render() == snapshot


def test_renderer_runtime_snapshot(empty_env: JinjaEnvironment, snapshot) -> None:
    """Runtime files are loadable via prefix loader with includes stripped."""
    tpl = dedent("""\
        {% include 'jsmn.h' %}
        {% include 'runtime.h' %}
        {% include 'runtime.c' %}
        """)
    assert empty_env.from_string(tpl).render() == snapshot


def test_renderer_hoist_includes(empty_env: JinjaEnvironment, snapshot) -> None:
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
