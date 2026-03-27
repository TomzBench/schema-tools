{% import 'functions.jinja2' as fn -%}
{% import 'decls.jinja2' as decls -%}

{% for d in descriptors | structs %}
#define {{ prefix | upper ~ d.ctype.name | upper }}_LEN ({{ d.encode_len }})
{% endfor %}
{% for a in descriptors | arrays if a is array_decl %}
#define {{ prefix | upper ~ a.ctype.name | upper }}_LEN ({{ a.encode_len }})
{% endfor %}

{# --- The C struct/union/enum/typedef declarations --- #}
{% for decl in declarations %}
{% if decl is struct_decl %}
{{ decls.struct(decl) }}
{% elif decl is union_decl %}
{{ decls.union(decl) }}
{% elif decl is array_decl %}
{{ decls.array_typedef(decl) }}
{% endif +%}
{% endfor -%}

{# --- Prototype declarations --- #}
{% for decl in declarations %}
{% if decl is struct_decl and decl is user_decl and not decl is array_decl %}
{{ fn.decode_prototype(prefix, decl.ctype.name, "struct") }}

{{ fn.encode_prototype(prefix, decl.ctype.name, "struct") }}

{% endif %}
{% endfor %}
{# --- Array prototype declarations --- #}
{% for a in descriptors | arrays if a is array_decl %}
{{ fn.decode_prototype(prefix, a.ctype.name, a.ctype | qualifier) }}

{{ fn.encode_prototype(prefix, a.ctype.name, a.ctype | qualifier) }}

{% endfor %}
