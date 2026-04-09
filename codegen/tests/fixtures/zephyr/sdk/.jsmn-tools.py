from pathlib import Path

from jsmn_tools.plugin.zephyr import load_zephyr_resource

def collect(config):
    root = Path(__file__).parent
    return [
        load_zephyr_resource(root / "schemas/common.openapi.yaml", "sdk", "common", 0),
        load_zephyr_resource(root / "schemas/auth.openapi.yaml", "sdk", "auth", 0),
    ]
