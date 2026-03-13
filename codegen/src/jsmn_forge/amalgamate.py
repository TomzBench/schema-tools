"""Amalgamate jsmn + jsmn_forge runtime into a single static C blob."""

from pathlib import Path

# Repository root paths for the C sources
_REPO_ROOT = Path(__file__).resolve().parents[4]
_JSMN_H = _REPO_ROOT / "include" / "jsmn.h"
_JSMN_FORGE_H = _REPO_ROOT / "include" / "jsmn_forge.h"
_JSMN_FORGE_C = _REPO_ROOT / "lib" / "jsmn_forge.c"


def amalgamate() -> str:
    """Produce the amalgamated static runtime blob.

    Returns a single C source string containing jsmn (JSMN_STATIC) +
    jsmn_forge types + jsmn_forge implementation, all with static linkage.
    """
    # TODO: read _JSMN_H, _JSMN_FORGE_H, _JSMN_FORGE_C
    # TODO: strip include guards, redundant #includes
    # TODO: wrap jsmn with JSMN_STATIC
    # TODO: make all jf_* functions static
    # TODO: return single string
    print("TODO: amalgamate not yet implemented")
    return ""
