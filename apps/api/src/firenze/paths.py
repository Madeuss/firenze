"""Where things are on disk.

One function computes the repository root, and everything that needs a path
under it derives from here. Getting `parents[n]` wrong is a mistake that looks
right, fails only at runtime, and has now been made twice — so it is made in a
single place.
"""

from pathlib import Path

# apps/api/src/firenze/paths.py -> firenze, src, api, apps, <root>
_DEPTH_FROM_ROOT = 4


class OutsideTheRepository(RuntimeError):
    """There is no repository root above this file.

    Happens in a container, where the package is installed at `/app/src` and
    counting four directories up runs out of path. The fix is never to count
    differently — it is to say where the files are: `FIRENZE_PROMPTS_DIR`.
    """


def repo_root() -> Path:
    here = Path(__file__).resolve()
    if len(here.parents) <= _DEPTH_FROM_ROOT:
        raise OutsideTheRepository(
            f"{here} is not inside a checkout — set FIRENZE_PROMPTS_DIR instead"
        )
    return here.parents[_DEPTH_FROM_ROOT]
