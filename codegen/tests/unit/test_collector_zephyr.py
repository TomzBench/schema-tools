from pathlib import Path

from jsmn_tools.collector.zephyr import collect


def test_collect() -> None:
    """Test that collect discovers all project specs and creates registry."""
    fixture = Path(__file__).parent.parent.absolute() / "fixtures" / "zephyr"
    projects = [fixture / mod for mod in fixture.iterdir() if mod.is_dir()]
    result = collect(projects, config={})

    assert not result.errors

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
    fixture = Path(__file__).parent.parent.absolute() / "fixtures" / "zephyr"
    projects = [fixture / mod for mod in fixture.iterdir() if mod.is_dir()]
    autoconf = {"BOARD": "native_sim", "CONFIG_BLE_ENABLED": "1"}
    result = collect(projects, config=autoconf)

    assert not result.errors
    assert len(result.registry.keys()) == 6


def test_collect_skips_dirs_without_config(tmp_path: Path) -> None:
    """Test that directories without .jsmn-tools.py are silently skipped."""
    (tmp_path / "no_config").mkdir()
    result = collect([tmp_path / "no_config"], config={})

    assert not result.errors
    assert len(result.registry.keys()) == 0


def test_collect_invalid_plugin(tmp_path: Path) -> None:
    """Test that a malformed plugin produces an InvalidPlugin error."""
    project = tmp_path / "bad"
    project.mkdir()
    config = project / ".jsmn-tools.py"
    config.write_text("def collect(autoconf):\n    return 'not a project'\n")
    result = collect([project], config={})

    assert len(result.errors) == 1
    assert len(result.registry.keys()) == 0
