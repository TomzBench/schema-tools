def collect(autoconf):
    return {
        "module": "sdk",
        "version": 0,
        "specs": {
            "common": "schemas/common.openapi.yaml",
            "auth": "schemas/auth.openapi.yaml",
        },
    }
