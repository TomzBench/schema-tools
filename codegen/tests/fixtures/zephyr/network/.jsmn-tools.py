def collect(autoconf):
    return {
        "module": "network",
        "version": 0,
        "specs": {
            "ethernet": "schemas/ethernet.openapi.yaml",
            "wifi": "schemas/wifi.openapi.yaml",
        },
    }
