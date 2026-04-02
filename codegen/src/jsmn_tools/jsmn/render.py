from __future__ import annotations

import re


def hoist_includes(text: str) -> str:
    """Deduplicate and hoist system includes to the top."""
    re_find = r"^#include\s+<[^>]*>.*$"
    re_sub = r"^#include\s+<[^>]*>.*\n"
    seen: set[str] = set()
    for m in re.finditer(re_find, text, re.MULTILINE):
        seen.add(m.group(0))
    body = re.sub(re_sub, "", text, flags=re.MULTILINE)
    return "\n".join(sorted(seen)) + "\n\n" + body if seen else text
