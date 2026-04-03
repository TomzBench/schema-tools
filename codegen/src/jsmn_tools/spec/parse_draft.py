from typing import Any

from jsmn_tools.node import ObjectNode

from .asyncapi_3_0 import obj_root as ASYNCAPI_3_0
from .openapi_3_1 import obj_root as OPENAPI_3_1


def parse_draft(content: Any) -> ObjectNode | None:
    drafts = {"openapi": OPENAPI_3_1, "asyncapi": ASYNCAPI_3_0}
    return next((d for k, d in drafts.items() if k in content), None)
