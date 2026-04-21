{% set struct_descriptors = descriptors | structs -%}
{% set array_descriptors = descriptors | arrays -%}
{% set field_descriptors = descriptors | fields -%}

{# --- Strings --- #}
static const char {{ prefix ~ "strings"}}[] =
{% for offset, name in strings %}
    "{{ name }}\0" /* {{ offset }} */
{% else %}
    ""
{% endfor -%}
;

{# --- Array Descriptors --- #}
static const struct jt_array {{ prefix ~ "arrays" }}[] = {
{% for a in array_descriptors %}
    /* [{{ loop.index0 }}] {{ a | comment }} */
    { {{ a | array_kind }}, 0, {{ a.max }}, {{ a | elem_size }}, {{ a | elem_expr }} },
{% else %}
    {0}
{% endfor -%}
};

{# --- Field Descriptors --- #}
static const struct jt_field {{ prefix ~ "fields" }}[] = {
{% for f in field_descriptors %}
    /* [{{ loop.index0 }}] {{ f | comment }} */
    { {{ f | name_offset }}, {{ f | value_offset }}, {{ f | present_offset }}, {{ f | type_expr }} },
{% else %}
    {0}
{% endfor -%}
};

{# --- Struct Descriptors --- #}
static const struct jt_struct {{ prefix ~ "structs" }}[] = {
{% for s in struct_descriptors %}
    /* [{{ loop.index0 }}] {{ s | comment }} */
    { {{ s.nfields }}, 0, {{ s | size_expr }}, {{ s.ntoks }}, {{ s.field0 }} },
{% else %}
    {0}
{% endfor -%}
};

{# --- Schemas Context --- #}
static const struct jt_schemas {{ prefix }}schemas = {
    .names   = {{ prefix }}strings,
    .arrays  = {{ prefix }}arrays,
    .fields  = {{ prefix }}fields,
    .structs = {{ prefix }}structs,
};

{# --- Polymorphic encode/decode --- #}
int32_t
{{ prefix }}decode(
    jsmntok_t *toks,
    uint32_t ntoks,
    void *dst,
    jt_type_t type,
    const char *src,
    uint32_t slen)
{
    return jt_decode(&{{ prefix ~ "schemas" }}, toks, ntoks, dst, type, src, slen);
}

int32_t
{{ prefix }}encode(
    uint8_t *dst,
    uint32_t dlen,
    const void *src,
    jt_type_t type)
{
	return jt_encode(&{{ prefix ~ "schemas" }}, dst, dlen, src, type);
}

int32_t
{{ prefix }}pack(
    uint8_t *dst,
    uint32_t dlen,
    const struct jt_part *parts,
    uint32_t n)
{
	return jt_pack(&{{ prefix ~ "schemas" }}, dst, dlen, parts, n);
}

int32_t
{{ prefix }}unpack(
    jsmntok_t *toks,
    uint32_t ntoks,
    const char *src,
    uint32_t slen,
    struct jt_part *parts,
    uint32_t n)
{
	return jt_unpack(&{{ prefix ~ "schemas" }}, toks, ntoks, src, slen, parts, n);
}

{# --- Shim Loop --- #}
{% for d in descriptors if d is public %}
{% set mode = d | shim_mode_or(default_shim_mode) %}
{% if mode == "extern" %}
{% set name = (d | type_prefix_or(prefix)) | upper ~ (d | nameify) | upper -%}
{% set ctype_decl = (d.ctype | qualifier ~ ' ' ~ d.ctype.name) | trim -%}
{% set decode = (d | method_name("decode", fallback_prefix=prefix)) -%}
{% set encode = (d | method_name("encode", fallback_prefix=prefix)) -%}

int32_t
{{ decode }}_tok(
    {{ ctype_decl }} *dst,
    const char *src,
    uint32_t slen,
    jsmntok_t *toks,
    uint32_t ntoks)
{
    return {{ prefix }}decode(toks, ntoks, dst, {{ name }}_KEY, src, slen);
}

int32_t
{{ decode }}(
    {{ ctype_decl }} *dst,
    const char *src,
    uint32_t slen)
{
    jsmntok_t toks[{{ name }}_NTOKS];
    return {{ decode }}_tok(dst, src, slen, toks, {{ name }}_NTOKS);
}

int32_t
{{ encode }}(
    uint8_t *dst,
    uint32_t dlen,
    const {{ ctype_decl }} *src)
{
	return {{ prefix }}encode(dst, dlen, src, {{ name }}_KEY);
}

{% endif %}
{% endfor %}
