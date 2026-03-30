from pathlib import Path

from schema_tools.bundle import bundle


def test_bundle_scan() -> None:
    """Test that bundle discovers all workspace modules and creates registry."""
    fixture = Path(__file__).parent.parent.absolute() / "fixtures" / "workspace"
    project = [fixture / module for module in fixture.iterdir()]
    registry = bundle("forge", project)
    resolver = registry.resolver()

    # Expected URIs (unordered)
    expected_keys = {
        "forge://sdk/common/v0",
        "forge://sdk/auth/v0",
        "forge://sensors/temperature/v0",
        "forge://sensors/humidity/v0",
        "forge://network/ethernet/v0",
        "forge://network/wifi/v0",
    }

    # Verify all expected keys are present
    actual_keys = set(registry.keys())
    assert actual_keys == expected_keys

    # Verify content keys match
    for k in registry:
        assert resolver.lookup(k).contents["$id"] == k
