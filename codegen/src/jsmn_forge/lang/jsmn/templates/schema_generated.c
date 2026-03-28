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


{# --- Schemas Context --- #}
static const struct rt_schemas {{ prefix }}schemas = {
    .names   = {{ prefix }}strings,
    .arrays  = {{ prefix }}arrays,
    .fields  = {{ prefix }}fields,
    .structs = {{ prefix }}structs,
};

{# --- Struct Loop --- #}
{% for s in struct_descriptors if s is user_decl %}
{% set idx = prefix | upper ~ s.ctype.name | upper ~ "_KEY" -%}
{% set type_expr = "RT_STRUCT(" ~ idx ~ ")" -%}

{# --- Struct Decode Function implementations --- #}
int32_t
{{ prefix }}decode_{{ s.ctype.name }}_tok(
    {{ ("struct" ~ ' ' ~ s.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen,
    jsmntok_t *toks,
    uint32_t ntoks)
{
    return rt_decode(&{{ prefix ~ "schemas" }}, toks, ntoks, dst, {{ type_expr }}, src, slen);
}

int32_t
{{ prefix }}decode_{{ s.ctype.name }}(
    {{ ("struct" ~ ' ' ~ s.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen)
{
    jsmntok_t toks[{{ s.ntoks }}];
    return {{ prefix }}decode_{{ s.ctype.name }}_tok(dst, src, slen, toks, {{ s.ntoks }});
}

{# --- Struct Encode Function implementations --- #}
int32_t
{{ prefix }}encode_{{ s.ctype.name }}(
    uint8_t *dst,
    uint32_t dlen,
    const {{ ("struct" ~ ' ' ~ s.ctype.name) | trim }} *src)
{
	return rt_encode(&{{ prefix ~ "schemas" }}, dst, dlen, src, {{ type_expr }});
}

{% endfor -%}

{# --- Array Loop --- #}
{% for a in descriptors | arrays if a is array_decl %}
{% set type_expr = "RT_ARRAY(" ~ a.key.pos ~ ")" -%}

{# --- Array Decode Tok Implementation --- #}
int32_t
{{ prefix }}decode_{{ a.ctype.name }}_tok(
    {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen,
    jsmntok_t *toks,
    uint32_t ntoks)
{
    return rt_decode(&{{ prefix ~ "schemas" }}, toks, ntoks, dst, {{ type_expr }}, src, slen);
}

{# --- Array Decode Implementation --- #}
int32_t
{{ prefix }}decode_{{ a.ctype.name }}(
    {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen)
{
    jsmntok_t toks[{{ a.ntoks }}];
    return {{ prefix }}decode_{{ a.ctype.name }}_tok(dst, src, slen, toks, {{ a.ntoks }});
}

{# --- Array Encode Implementation --- #}
int32_t
{{ prefix }}encode_{{ a.ctype.name }}(
    uint8_t *dst,
    uint32_t dlen,
    const {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *src)
{
	return rt_encode(&{{ prefix ~ "schemas" }}, dst, dlen, src, {{ type_expr }});
}

{% endfor %}
