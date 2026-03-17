{% import 'functions.jinja2' as fn -%}
{% import 'decls.jinja2' as decls -%}

{% for d in descriptors | structs %}
#define {{ prefix | upper ~ d.ctype.name | upper }}_LEN ({{ d.encode_len }})
{% endfor %}

{# --- The C struct/union/enum declarations --- #}
{% for decl in declarations %}
{% if decl is struct_decl %}
{{ decls.struct(decl) }}
{% elif decl is union_decl %}
{{ decls.union(decl) }}
{% endif +%}
{% endfor -%}

{# --- Prototype declarations --- #}
{% for decl in declarations %}
{% if decl is struct_decl and decl is user_decl %}
{{ fn.decode_prototype(prefix, decl.ctype.name) }}

{{ fn.encode_prototype(prefix, decl.ctype.name) }}

{% endif %}
{% endfor %}
