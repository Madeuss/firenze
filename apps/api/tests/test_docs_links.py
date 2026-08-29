"""Relative links in the repository's Markdown have to resolve.

This lives in the API test suite because that is the only runner the CI has,
and a separate workflow would mean another required check to keep green. A
broken link in a public repository is a small thing that reads as carelessness
in the documents this project is partly judged on.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
MARKDOWN = sorted(
    path
    for path in REPO.rglob("*.md")
    if not any(part in {".venv", "node_modules", ".git"} for part in path.parts)
)
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_the_suite_actually_found_the_documents() -> None:
    """A glob that silently matches nothing would make every assertion below pass."""
    assert len(MARKDOWN) >= 10


@pytest.mark.parametrize("document", MARKDOWN, ids=lambda p: str(p.relative_to(REPO)))
def test_relative_links_resolve(document: Path) -> None:
    broken = []
    for target in LINK.findall(document.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if not (document.parent / target.split("#")[0]).exists():
            broken.append(target)

    assert not broken, f"{document.relative_to(REPO)} points at: {broken}"
