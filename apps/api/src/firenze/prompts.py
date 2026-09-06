"""Where versioned prompts live.

Repository `prompts/`, or wherever `FIRENZE_PROMPTS_DIR` points. Shared because
two packages need it and neither should have to import the other to find a
directory.
"""

import os
from pathlib import Path

from firenze.paths import repo_root


def prompts_dir() -> Path:
    override = os.environ.get("FIRENZE_PROMPTS_DIR")
    if override:
        return Path(override)
    return repo_root() / "prompts"
