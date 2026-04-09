from pathlib import Path

from jsmn_tools.plugin.zephyr import load_zephyr_resource

def collect(config):
    root = Path(__file__).parent
    return [
        load_zephyr_resource(root / "schemas/ethernet.openapi.yaml", "network", "ethernet", 0),
        load_zephyr_resource(root / "schemas/wifi.openapi.yaml", "network", "wifi", 0),
    ]
