{% for d in descriptors | structs %}
#define {{ prefix | upper ~ d.ctype.name | upper }}_LEN ({{ d.encode_len }})
{% endfor %}
{% for a in descriptors | arrays if a is array_decl %}
#define {{ prefix | upper ~ a.ctype.name | upper }}_LEN ({{ a.encode_len }})
{% endfor %}

{# --- The C struct/union/enum/typedef declarations --- #}
{% for decl in declarations %}
{% if decl is struct_decl %}
struct {{ decl.ctype.name }} {
{% for f in decl.fields %}
    {{ (f.ctype | qualifier ~ ' ' ~ f.ctype.name) | trim }} {{ f.name }}{{ f.ctype.dims | dimensions }};
{% endfor %}
};
{% elif decl is union_decl %}
union {{ decl.ctype.name }} {
{% for v in decl.variants %}
    {{ (v.ctype | qualifier ~ ' ' ~ v.ctype.name) | trim }} {{ v.name }}{{ v.ctype.dims | dimensions }};
{% endfor %}
};
{% elif decl is array_decl %}
typedef {{ (decl.elem | qualifier ~ ' ' ~ decl.elem.name) | trim }} {{ decl.ctype.name }}[{{ decl.max }}];
{% endif +%}
{% endfor -%}

{# --- Prototype declarations --- #}
{% for decl in declarations %}
{% if decl is struct_decl and decl is user_decl and not decl is array_decl %}
int32_t {{ prefix }}decode_{{ decl.ctype.name }}_tok(
    {{ ("struct" ~ ' ' ~ decl.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen,
    jsmntok_t *toks,
    uint32_t ntoks);

int32_t {{ prefix }}decode_{{ decl.ctype.name }}(
    {{ ("struct" ~ ' ' ~ decl.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen);

int32_t {{ prefix }}encode_{{ decl.ctype.name }}(
    uint8_t *dst,
    uint32_t dlen,
    const {{ ("struct" ~ ' ' ~ decl.ctype.name) | trim }} *src);

{% endif %}
{% endfor %}
{# --- Array prototype declarations --- #}
{% for a in descriptors | arrays if a is array_decl %}
int32_t {{ prefix }}decode_{{ a.ctype.name }}_tok(
    {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen,
    jsmntok_t *toks,
    uint32_t ntoks);

int32_t {{ prefix }}decode_{{ a.ctype.name }}(
    {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen);

int32_t {{ prefix }}encode_{{ a.ctype.name }}(
    uint8_t *dst,
    uint32_t dlen,
    const {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *src);

{% endfor %}
