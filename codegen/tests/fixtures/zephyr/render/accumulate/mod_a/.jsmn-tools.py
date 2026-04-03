def collect(autoconf):
    return {
        "module": "mod_a",
        "version": 0,
        "specs": {"mod_a": "schemas/mod_a.openapi.yaml"},
        "jinja_filters": {"shout": lambda s: s.upper()},
    }
