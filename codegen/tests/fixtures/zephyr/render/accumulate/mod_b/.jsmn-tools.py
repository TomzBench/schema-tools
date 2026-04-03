def collect(autoconf):
    return {
        "module": "mod_b",
        "version": 0,
        "specs": {"mod_b": "schemas/mod_b.openapi.yaml"},
        "render": [("tpl.jinja2", "out.txt")],
    }
