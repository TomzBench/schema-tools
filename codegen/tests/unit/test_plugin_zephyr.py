import shutil
from pathlib import Path

from jsmn_tools.plugin.zephyr import (
    JinjaFilterExists,
    JinjaTestExists,
    collect,
    render,
)

FIXTURE = Path(__file__).parent.parent.absolute() / "fixtures" / "zephyr"
RENDER = FIXTURE / "render"


def _workspace(root: Path) -> list[Path]:
    return [root / d for d in root.iterdir() if d.is_dir()]


def test_collect() -> None:
    """Test that collect discovers all project specs and creates registry."""
    result = collect(_workspace(FIXTURE), config={})

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


def test_collect_returns_loaded_projects() -> None:
    """Test that collect returns loaded project configs with their dirs."""
    result = collect(_workspace(FIXTURE), config={})

    assert len(result.projects) == 3
    modules = {p["module"] for p in result.projects}
    assert modules == {"sdk", "sensors", "network"}
    for p in result.projects:
        assert p["dir"].is_dir()


def test_collect_with_autoconf() -> None:
    """Test that autoconf dict is passed to .jsmn-tools.py collect()."""
    autoconf = {"BOARD": "native_sim", "CONFIG_BLE_ENABLED": "1"}
    result = collect(_workspace(FIXTURE), config=autoconf)

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


def test_render_accumulates_filters(tmp_path: Path, snapshot) -> None:
    """Test that jinja_filters from one plugin are available to another."""
    ws = tmp_path / "ws"
    shutil.copytree(RENDER / "accumulate", ws)
    result = collect(_workspace(ws), config={})
    assert not result.errors

    errors = render(result)
    assert not errors
    assert (ws / "mod_b" / "out.txt").read_text() == snapshot


def test_render_filter_collision_keeps_first(tmp_path: Path, snapshot) -> None:
    """Test that duplicate filter names produce JinjaFilterExists, first wins."""
    ws = tmp_path / "ws"
    shutil.copytree(RENDER / "collision_filter", ws)
    result = collect(_workspace(ws), config={})
    errors = render(result)

    dupes = [e for e in errors if isinstance(e, JinjaFilterExists)]
    assert len(dupes) == 1
    assert "dup" in str(dupes[0])
    assert (ws / "mod_b" / "out.txt").read_text() == snapshot


def test_render_test_collision(tmp_path: Path) -> None:
    """Test that duplicate jinja_tests names produce JinjaTestExists."""
    result = collect(_workspace(RENDER / "collision_test"), config={})
    errors = render(result)

    dupes = [e for e in errors if isinstance(e, JinjaTestExists)]
    assert len(dupes) == 1
    assert "cool" in str(dupes[0])
