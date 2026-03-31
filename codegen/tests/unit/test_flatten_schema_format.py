from typing import Any

from jsmn_tools.lang.jsmn.flatten import (
    UnsupportedSchemaFormat,
    flatten_with_resolver,
)
from jsmn_tools.spec import ASYNCAPI_3_0
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


def _registry(*specs: dict[str, Any]) -> Registry:
    resources = [
        Resource.from_contents(s, default_specification=DRAFT202012) for s in specs
    ]
    return resources @ Registry()


def test_schema_format_emits_error() -> None:
    """schemaFormat in a schema_enter position produces UnsupportedSchemaFormat."""
    spec: dict[str, Any] = {
        "$id": "forge://test/res/v0",
        "asyncapi": "3.0.0",
        "info": {"title": "t", "version": "0"},
        "channels": {
            "ch": {
                "messages": {
                    "msg": {
                        "payload": {
                            "schemaFormat": "application/vnd.apache.avro;version=1.9.0",
                            "schema": {"type": "object", "properties": {}},
                        }
                    }
                }
            }
        },
    }
    reg = _registry(spec)
    specs = [r.contents for x in reg if (r := reg.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=reg.resolver(), draft=ASYNCAPI_3_0)
    fmt_errors = [e for e in result.errors if isinstance(e, UnsupportedSchemaFormat)]
    assert len(fmt_errors) == 1
    assert "avro" in fmt_errors[0].schema_format.lower()


def test_direct_schema_no_error() -> None:
    """Direct JSON Schema payload (Form A) produces no UnsupportedSchemaFormat."""
    spec: dict[str, Any] = {
        "$id": "forge://test/res/v0",
        "asyncapi": "3.0.0",
        "info": {"title": "t", "version": "0"},
        "channels": {
            "ch": {
                "messages": {
                    "msg": {
                        "payload": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        }
                    }
                }
            }
        },
    }
    reg = _registry(spec)
    specs = [r.contents for x in reg if (r := reg.get(x)) is not None]
    result = flatten_with_resolver(*specs, resolver=reg.resolver(), draft=ASYNCAPI_3_0)
    fmt_errors = [e for e in result.errors if isinstance(e, UnsupportedSchemaFormat)]
    assert len(fmt_errors) == 0
