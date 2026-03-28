{% import 'functions.jinja2' as fn -%}
{% set struct_descriptors = descriptors | structs -%}
{% set array_descriptors = descriptors | arrays -%}
{% set field_descriptors = descriptors | fields -%}

{# --- Strings --- #}
static const char {{ prefix ~ "strings"}}[] =
{% for offset, name in strings %}
    "{{ name }}\0" /* {{ offset }} */
{% endfor -%}
;

{# --- Array Descriptors --- #}
static const struct rt_array {{ prefix ~ "arrays" }}[] = {
{% for a in array_descriptors %}
    /* [{{ loop.index0 }}] {{ a | comment }} */
    { {{ a | array_kind }}, 0, {{ a.max }}, {{ a | elem_size }}, {{ a | elem_expr }} },
{% endfor -%}
};

{# --- Field Descriptors --- #}
static const struct rt_field {{ prefix ~ "fields" }}[] = {
{% for f in field_descriptors %}
    /* [{{ loop.index0 }}] {{ f | comment }} */
    { {{ f | name_offset }}, {{ f | value_offset }}, {{ f | present_offset }}, {{ f | type_expr }} },
{% endfor -%}
};

{# --- Struct Descriptors --- #}
static const struct rt_struct {{ prefix ~ "structs" }}[] = {
{% for s in struct_descriptors %}
    /* [{{ loop.index0 }}] {{ s | comment }} */
    { {{ s.nfields }}, 0, {{ s | size_expr }}, {{ s.ntoks }}, {{ s.field0 }} },
{% endfor -%}
};

{# --- Struct Keys --- #}
{% for d in struct_descriptors %}
#define {{ prefix | upper }}{{ d.ctype.name | upper }}_KEY {{ loop.index0 }}
{% endfor %}


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
