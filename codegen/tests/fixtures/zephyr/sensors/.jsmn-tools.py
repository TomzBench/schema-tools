from pathlib import Path

from jsmn_tools.plugin.zephyr import load_zephyr_resource

def collect(config):
    root = Path(__file__).parent
    return [
        load_zephyr_resource(root / "schemas/temperature.openapi.yaml", "sensors", "temperature", 0),
        load_zephyr_resource(root / "schemas/humidity.openapi.yaml", "sensors", "humidity", 0),
    ]
