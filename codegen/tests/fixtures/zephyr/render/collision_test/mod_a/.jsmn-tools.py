def collect(autoconf):
    return {
        "module": "mod_a",
        "version": 0,
        "specs": {"mod_a": "schemas/mod_a.openapi.yaml"},
        "jinja_tests": {"cool": lambda x: True},
    }
