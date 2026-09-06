"""Where things are on disk.

One function computes the repository root, and everything that needs a path
under it derives from here. Getting `parents[n]` wrong is a mistake that looks
right, fails only at runtime, and has now been made twice — so it is made in a
single place.
"""

from pathlib import Path

# apps/api/src/firenze/paths.py -> firenze, src, api, apps, <root>
_DEPTH_FROM_ROOT = 4


def repo_root() -> Path:
    return Path(__file__).resolve().parents[_DEPTH_FROM_ROOT]
