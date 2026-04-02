def collect(autoconf):
    return {
        "module": "sensors",
        "version": 0,
        "specs": {
            "temperature": "schemas/temperature.openapi.yaml",
            "humidity": "schemas/humidity.openapi.yaml",
        },
    }
