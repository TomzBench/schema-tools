{% import 'tables.jinja2' as tables -%}
{% import 'functions.jinja2' as fn -%}
{% set struct_descriptors = descriptors | structs -%}
{% set array_descriptors = descriptors | arrays -%}
{% set field_descriptors = descriptors | fields -%}

{{ tables.strings(prefix ~ "strings", strings) }}

{{ tables.arrays(prefix ~ "arrays", array_descriptors) }}

{{ tables.fields(prefix ~ "fields", field_descriptors) }}

{{ tables.structs(prefix ~ "structs", struct_descriptors) }}

{{ tables.keys(prefix, struct_descriptors) }}

static const struct rt_schemas {{ prefix }}schemas = {
    .names   = {{ prefix }}strings,
    .arrays  = {{ prefix }}arrays,
    .fields  = {{ prefix }}fields,
    .structs = {{ prefix }}structs,
};

{# --- Struct function implementations --- #}
{% for s in struct_descriptors if s is user_decl %}
{% set idx = prefix | upper ~ s.ctype.name | upper ~ "_KEY" -%}
{% set type_expr = "RT_STRUCT(" ~ idx ~ ")" -%}
{{ fn.decode(prefix, s.ctype.name, s.ntoks, type_expr, prefix ~ "schemas", "struct") }}

{{ fn.encode(prefix, s.ctype.name, type_expr, prefix ~ "schemas", "struct") }}

{% endfor %}
{# --- Array function implementations --- #}
{% for a in descriptors | arrays if a is array_decl %}
{% set type_expr = "RT_ARRAY(" ~ a.key.pos ~ ")" -%}
{{ fn.decode(prefix, a.ctype.name, a.ntoks, type_expr, prefix ~ "schemas", a.ctype | qualifier) }}

{{ fn.encode(prefix, a.ctype.name, type_expr, prefix ~ "schemas", a.ctype | qualifier) }}

{% endfor %}
