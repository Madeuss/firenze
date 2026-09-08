"""The threat model has to keep being true.

`docs/05-threat-model.md` claims a mitigation is proved by naming the test that
proves it. A document that names tests which no longer exist is worse than no
document: it reads as evidence and is not.

So the names are checked here. Deleting or renaming a cited test fails this,
which is the moment to decide whether the mitigation still holds — or whether
that line belongs back under "abertas".
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DOCUMENT = REPO / "docs" / "05-threat-model.md"
TESTS = Path(__file__).resolve().parent

CITED = re.compile(r"`(test_[a-z0-9_]+)`")
DEFINED = re.compile(r"^def (test_[a-z0-9_]+)", re.MULTILINE)


def _defined() -> set[str]:
    return {
        name
        for path in TESTS.glob("test_*.py")
        for name in DEFINED.findall(path.read_text(encoding="utf-8"))
    }


def test_the_threat_model_exists_and_names_its_evidence() -> None:
    """A regex that matched nothing would make the assertion below vacuous."""
    assert DOCUMENT.exists()
    assert len(CITED.findall(DOCUMENT.read_text(encoding="utf-8"))) >= 20


def test_every_test_the_threat_model_cites_exists() -> None:
    cited = set(CITED.findall(DOCUMENT.read_text(encoding="utf-8")))

    missing = sorted(cited - _defined())

    assert not missing, f"the threat model cites tests that do not exist: {missing}"
