from __future__ import annotations

from enum import StrEnum

from jsmn_forge.node import (
    _NO_BHV,
    Behavior,
    DraftKeys,
    MapNode,
    ObjectNode,
    canonical,
    data,
    identity_key,
)

from .json_schema import map_schema_enter, schema_enter

_param_key = identity_key("in", "name")


class OpenAPIKind(StrEnum):
    # Object nodes
    ROOT = "root"
    INFO = "info"
    COMPONENTS = "components"
    PATH_ITEM = "path_item"
    OPERATION = "operation"
    PARAMETER = "parameter"
    REQUEST_BODY = "request_body"
    RESPONSE = "response"
    MEDIA_TYPE = "media_type"
    ENCODING = "encoding"
    SERVER = "server"
    SERVER_VAR = "server_var"
    LINK = "link"
    # Map nodes
    MAP_PATH_ITEM = "map_path_item"
    MAP_RESPONSE = "map_response"
    MAP_CONTENT = "map_content"
    MAP_HEADER = "map_header"
    MAP_ENCODING = "map_encoding"
    MAP_PARAMETER = "map_parameter"
    MAP_REQUEST_BODY = "map_request_body"
    MAP_LINK = "map_link"
    MAP_CALLBACK = "map_callback"
    MAP_SERVER_VAR = "map_server_var"
    MAP_SCOPE = "map_scope"


obj_root: ObjectNode[DraftKeys[OpenApi31Keys]] = ObjectNode(OpenAPIKind.ROOT)
obj_info = ObjectNode(OpenAPIKind.INFO)
obj_components = ObjectNode(OpenAPIKind.COMPONENTS)
obj_path_item = ObjectNode(OpenAPIKind.PATH_ITEM)
obj_operation = ObjectNode(OpenAPIKind.OPERATION)
obj_parameter = ObjectNode(OpenAPIKind.PARAMETER)
obj_request_body = ObjectNode(OpenAPIKind.REQUEST_BODY)
obj_response = ObjectNode(OpenAPIKind.RESPONSE)
obj_media_type = ObjectNode(OpenAPIKind.MEDIA_TYPE)
obj_encoding = ObjectNode(OpenAPIKind.ENCODING)
obj_server = ObjectNode(OpenAPIKind.SERVER)
obj_server_var = ObjectNode(OpenAPIKind.SERVER_VAR)
obj_link = ObjectNode(OpenAPIKind.LINK)

map_path_item = MapNode(OpenAPIKind.MAP_PATH_ITEM)
map_response = MapNode(OpenAPIKind.MAP_RESPONSE)
map_content = MapNode(OpenAPIKind.MAP_CONTENT)
map_header = MapNode(OpenAPIKind.MAP_HEADER)
map_encoding = MapNode(OpenAPIKind.MAP_ENCODING)
map_parameter = MapNode(OpenAPIKind.MAP_PARAMETER)
map_request_body = MapNode(OpenAPIKind.MAP_REQUEST_BODY)
map_link = MapNode(OpenAPIKind.MAP_LINK)
map_callback = MapNode(OpenAPIKind.MAP_CALLBACK)
map_server_var = MapNode(OpenAPIKind.MAP_SERVER_VAR)
map_scope = MapNode(OpenAPIKind.MAP_SCOPE)


# fmt: off
obj_root.configure(table={
    "paths":            (map_path_item, _NO_BHV),
    "webhooks":         (map_path_item, _NO_BHV),
    "components":       (obj_components, _NO_BHV),
    "servers":          (obj_server, _NO_BHV),
    "security":         (map_scope, Behavior(sort_key=canonical)),
})

obj_info.configure(table={})

obj_components.configure(table={
    "schemas":          (map_schema_enter, _NO_BHV),
    "parameters":       (map_parameter, _NO_BHV),
    "headers":          (map_header, _NO_BHV),
    "requestBodies":    (map_request_body, _NO_BHV),
    "responses":        (map_response, _NO_BHV),
    "pathItems":        (map_path_item, _NO_BHV),
    "callbacks":        (map_callback, _NO_BHV),
    "links":            (map_link, _NO_BHV),
})

obj_path_item.configure(table={
    "get":              (obj_operation, _NO_BHV),
    "put":              (obj_operation, _NO_BHV),
    "post":             (obj_operation, _NO_BHV),
    "delete":           (obj_operation, _NO_BHV),
    "options":          (obj_operation, _NO_BHV),
    "head":             (obj_operation, _NO_BHV),
    "patch":            (obj_operation, _NO_BHV),
    "trace":            (obj_operation, _NO_BHV),
    "parameters":       (obj_parameter, Behavior(sort_key=_param_key)),
    "servers":          (obj_server, _NO_BHV),
})

obj_operation.configure(table={
    "requestBody":      (obj_request_body, _NO_BHV),
    "responses":        (map_response, _NO_BHV),
    "callbacks":        (map_callback, _NO_BHV),
    "parameters":       (obj_parameter, Behavior(sort_key=_param_key)),
    "servers":          (obj_server, _NO_BHV),
    "security":         (map_scope, Behavior(sort_key=canonical)),
    "tags":             (data, Behavior(sort_key=str)),
})

obj_parameter.configure(table={
    "schema":           (schema_enter, _NO_BHV),
    "content":          (map_content, _NO_BHV),
})

obj_request_body.configure(table={
    "content":          (map_content, _NO_BHV),
})

obj_response.configure(table={
    "content":          (map_content, _NO_BHV),
    "headers":          (map_header, _NO_BHV),
    "links":            (map_link, _NO_BHV),
})

obj_media_type.configure(table={
    "schema":           (schema_enter, _NO_BHV),
    "encoding":         (map_encoding, _NO_BHV),
})

obj_encoding.configure(table={
    "headers":          (map_header, _NO_BHV),
})

obj_server.configure(table={
    "variables":        (map_server_var, _NO_BHV),
})

obj_server_var.configure(table={
    "enum":             (data, Behavior(sort_key=str)),
})

obj_link.configure(table={
    "server":           (obj_server, _NO_BHV),
})

map_path_item.configure(child=obj_path_item)
map_response.configure(child=obj_response)
map_content.configure(child=obj_media_type)
map_header.configure(child=obj_parameter)
map_encoding.configure(child=obj_encoding)
map_parameter.configure(child=obj_parameter)
map_request_body.configure(child=obj_request_body)
map_link.configure(child=obj_link)
map_callback.configure(child=map_path_item)
map_server_var.configure(child=obj_server_var)
map_scope.configure(child=data, behavior=Behavior(sort_key=str))
# fmt: on

type OpenApi31Keys = DraftKeys[OpenAPIKind]
