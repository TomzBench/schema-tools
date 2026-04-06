import shutil
from pathlib import Path

import pytest

from jsmn_tools.plugin.zephyr import collect, render

FIXTURE = Path(__file__).parent.parent.absolute() / "fixtures" / "zephyr"
RENDER = FIXTURE / "render"


def _workspace(root: Path) -> list[Path]:
    return [root / d for d in root.iterdir() if d.is_dir()]


def test_collect() -> None:
    """Test that collect discovers all project specs and creates registry."""
    result = collect(_workspace(FIXTURE), config={})

    expected_keys = {
        "zephyr://sdk/common/v0",
        "zephyr://sdk/auth/v0",
        "zephyr://sensors/temperature/v0",
        "zephyr://sensors/humidity/v0",
        "zephyr://network/ethernet/v0",
        "zephyr://network/wifi/v0",
    }

    actual_keys = set(result.registry.keys())
    assert actual_keys == expected_keys

    resolver = result.registry.resolver()
    for k in result.registry:
        assert resolver.lookup(k).contents["$id"] == k


def test_collect_with_autoconf() -> None:
    """Test that autoconf dict is passed to .jsmn-tools.py collect()."""
    autoconf = {"BOARD": "native_sim", "CONFIG_BLE_ENABLED": "1"}
    result = collect(_workspace(FIXTURE), config=autoconf)

    assert len(result.registry.keys()) == 6


def test_collect_skips_dirs_without_config(tmp_path: Path) -> None:
    """Test that directories without .jsmn-tools.py are silently skipped."""
    (tmp_path / "no_config").mkdir()
    result = collect([tmp_path / "no_config"], config={})

    assert len(result.registry.keys()) == 0


def test_collect_invalid_plugin(tmp_path: Path) -> None:
    """Test that a malformed plugin raises during collect."""
    project = tmp_path / "bad"
    project.mkdir()
    config = project / ".jsmn-tools.py"
    config.write_text("def collect(autoconf):\n    return 'not a project'\n")

    with pytest.raises(Exception):
        collect([project], config={})


def test_render_accumulates_filters(tmp_path: Path, snapshot) -> None:
    """Test that extend hooks from one plugin are available to another."""
    ws = tmp_path / "ws"
    shutil.copytree(RENDER / "accumulate", ws)
    result = collect(_workspace(ws), config={})

    errors = render(result)
    assert not errors
    assert (ws / "mod_b" / "out.txt").read_text() == snapshot
