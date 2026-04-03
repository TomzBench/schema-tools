{% for d in descriptors | structs %}
#define {{ d | type_prefix_or(prefix) | upper }}{{ d | nameify | upper }}_LEN ({{ d.encode_len }})
{% endfor %}
{% for a in descriptors | arrays if a is array_decl %}
#define {{ a | type_prefix_or(prefix) | upper }}{{ a | nameify | upper }}_LEN ({{ a.encode_len }})
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

{# --- Polymorphic encode/decode --- #}
int32_t {{ prefix }}decode(
    jsmntok_t *toks,
    uint32_t ntoks,
    void *dst,
    jt_type_t type,
    const char *src,
    uint32_t slen);

int32_t {{ prefix }}encode(
    uint8_t *dst,
    uint32_t dlen,
    const void *src,
    jt_type_t type);

{# --- Prototype declarations --- #}
{% for decl in declarations %}
{% if decl is struct_decl and decl is user_decl and not decl is array_decl %}
int32_t {{ decl | method_name("decode", fallback_prefix=prefix) }}_tok(
    {{ ("struct" ~ ' ' ~ decl.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen,
    jsmntok_t *toks,
    uint32_t ntoks);

int32_t {{ decl | method_name("decode", fallback_prefix=prefix) }}(
    {{ ("struct" ~ ' ' ~ decl.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen);

int32_t {{ decl | method_name("encode", fallback_prefix=prefix) }}(
    uint8_t *dst,
    uint32_t dlen,
    const {{ ("struct" ~ ' ' ~ decl.ctype.name) | trim }} *src);

{% endif %}
{% endfor %}
{# --- Array prototype declarations --- #}
{% for a in descriptors | arrays if a is array_decl %}
int32_t {{ a | method_name("decode", fallback_prefix=prefix) }}_tok(
    {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen,
    jsmntok_t *toks,
    uint32_t ntoks);

int32_t {{ a | method_name("decode", fallback_prefix=prefix) }}(
    {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *dst,
    const char *src,
    uint32_t slen);

int32_t {{ a | method_name("encode", fallback_prefix=prefix) }}(
    uint8_t *dst,
    uint32_t dlen,
    const {{ (a.ctype | qualifier ~ ' ' ~ a.ctype.name) | trim }} *src);

{% endfor %}
