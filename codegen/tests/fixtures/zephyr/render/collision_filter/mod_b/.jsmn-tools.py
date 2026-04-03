def collect(autoconf):
    return {
        "module": "mod_b",
        "version": 0,
        "specs": {"mod_b": "schemas/mod_b.openapi.yaml"},
        "jinja_filters": {"dup": lambda s: "SECOND"},
        "render": [("tpl.jinja2", "out.txt")],
    }
