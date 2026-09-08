"""Where the code looks for files it did not import.

These exist because the container found the bug the checkout could not: the
package installs at `/app/src`, so counting four directories up runs out of
path, and every turn died looking for a prompt. `repo_root()` is right in a
checkout and meaningless outside one — so the override has to work, and the
failure has to say what to do.
"""

import pathlib

import pytest

from firenze.paths import OutsideTheRepository, repo_root
from firenze.prompts import prompts_dir


def test_the_repository_root_is_the_one_holding_the_apps() -> None:
    root = repo_root()

    assert (root / "apps" / "api").is_dir()
    assert (root / "prompts").is_dir()


def test_prompts_default_to_the_directory_in_the_repository() -> None:
    assert prompts_dir() == repo_root() / "prompts"
    assert (prompts_dir() / "npc").is_dir()


def test_an_explicit_prompts_directory_wins(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """How a container says where the prompts are, instead of counting."""
    monkeypatch.setenv("FIRENZE_PROMPTS_DIR", str(tmp_path))

    assert prompts_dir() == tmp_path


def test_an_explicit_directory_is_not_asked_to_find_a_repository(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The override has to come first, not as a fallback after the maths.

    In the image there is no root to find, so `repo_root()` raising would take
    the process down before the override was ever read.
    """
    monkeypatch.setenv("FIRENZE_PROMPTS_DIR", str(tmp_path))
    monkeypatch.setattr(
        "firenze.prompts.repo_root",
        lambda: (_ for _ in ()).throw(OutsideTheRepository("no checkout here")),
    )

    assert prompts_dir() == tmp_path


def test_outside_a_checkout_the_failure_says_what_to_do(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An IndexError from `parents[4]` explains nothing to whoever hits it."""
    monkeypatch.setattr("firenze.paths.__file__", "/app/src/firenze/paths.py")

    with pytest.raises(OutsideTheRepository, match="FIRENZE_PROMPTS_DIR"):
        repo_root()
