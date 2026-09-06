"""Parser tests. (RN-031, RN-032)

The property under test is that the parser cannot commit anything. It fills a
form; the player sends the form back. So most of these check what happens to
input the parser could have guessed at and did not.
"""

from typing import Any

import pytest

from firenze.accusation import Draft, known_motives, parse, render, summarise, tidy
from firenze.domain import FactKind, Match, Stance, Statement
from firenze.generation import generate
from firenze.i18n import load


def _match(holding: tuple[str, ...] = ()) -> Match:
    given = tuple(
        Statement(
            turn=i + 1,
            character="sus-2",
            question="?",
            line="...",
            stance=Stance.cooperative,
            lied=False,
            clue_revealed=fact_id,
        )
        for i, fact_id in enumerate(holding)
    )
    return Match(full_case=generate(seed=42), locale="pt-BR", statements=given)


def _motive_fact_id(match: Match) -> str:
    return next(f.id for f in match.case.facts if f.kind is FactKind.motive)


class Parser:
    def __init__(self, draft: Draft) -> None:
        self._draft = draft
        self.prompts: list[str] = []

    @property
    def name(self) -> str:
        return "parser"

    def complete(self, **kwargs: Any) -> Any:
        self.prompts.append(kwargs["system"])
        return self._draft


# --- what the parser is allowed to see ------------------------------------


def test_the_parser_is_shown_only_evidence_the_player_holds() -> None:
    """It cannot offer, on the player's behalf, something they were never told."""
    match = _match()
    system, _ = render(match, load("pt-BR"), "foi o mordomo")

    for fact in match.case.facts:
        if fact.id in match.evidence:
            continue
        assert f"- {fact.id}:" not in system


def test_a_player_who_never_found_the_motive_is_offered_none() -> None:
    """Twenty points is not a one-in-four guess handed over in a dropdown."""
    assert known_motives(_match()) == ()


def test_finding_the_quarrel_makes_its_motive_nameable() -> None:
    match = _match()
    holding = _match(holding=(_motive_fact_id(match),))

    assert known_motives(holding) == (match.full_case.solution.motive_key,)


def test_a_long_ramble_is_truncated_before_parsing() -> None:
    match = _match()

    _, user = render(match, load("pt-BR"), "a" * 5000)

    assert len(user) < 1200


# --- what it does with what it cannot place -------------------------------


def test_a_suspect_who_is_not_in_the_case_is_not_guessed_at() -> None:
    """A wrong guess becomes an accusation the player never made."""
    match = _match()

    tidied = tidy(Draft(culprit="sus-99"), match)

    assert tidied.culprit is None
    assert any("sus-99" in u for u in tidied.unresolved)


def test_evidence_the_player_does_not_hold_is_dropped_and_reported() -> None:
    match = _match()
    unheld = next(f.id for f in match.case.facts if f.id not in match.evidence)

    tidied = tidy(Draft(culprit="sus-1", evidence=(unheld, "F-001")), match)

    assert tidied.evidence == ("F-001",)
    assert any(unheld in u for u in tidied.unresolved)


def test_a_motive_they_never_found_is_dropped() -> None:
    match = _match()

    tidied = tidy(Draft(culprit="sus-1", motive_key="inheritance"), match)

    assert tidied.motive_key is None
    assert any("inheritance" in u for u in tidied.unresolved)


def test_a_motive_they_did_find_survives() -> None:
    match = _match()
    holding = _match(holding=(_motive_fact_id(match),))
    real = match.full_case.solution.motive_key

    assert tidy(Draft(culprit="sus-1", motive_key=real), holding).motive_key == real


def test_what_the_player_said_that_matched_nothing_comes_back_to_them() -> None:
    tidied = tidy(Draft(unresolved=("o jardineiro",)), _match())

    assert "o jardineiro" in tidied.unresolved


# --- the confirmation -----------------------------------------------------


def test_the_summary_says_what_is_about_to_happen() -> None:
    match = _match()
    catalog = load("pt-BR")

    summary = summarise(Draft(culprit="sus-1", evidence=("F-001",)), match.case, catalog)

    assert match.case.name_of("sus-1") in summary
    assert "não pode ser desfeito" in summary


def test_an_empty_draft_still_reads_as_a_sentence() -> None:
    """A player who typed something unusable sees that, rather than a blank form."""
    summary = summarise(Draft(), _match().case, load("pt-BR"))

    assert "ninguém" in summary
    assert "sem provas" in summary


def test_parsing_returns_a_draft_and_commits_nothing() -> None:
    match = _match()
    model = Parser(Draft(culprit="sus-1", evidence=("F-001",)))

    draft = parse(match, load("pt-BR"), "foi a Vitória, o corpo estava lá", model=model)

    assert draft.culprit == "sus-1"
    assert not match.is_over, "nothing was decided"


def test_nothing_in_this_module_can_decide_an_outcome() -> None:
    """The parser fills a form. `firenze.verdict` is what judges one."""
    import pathlib

    source = pathlib.Path(__file__).resolve().parents[1] / "src" / "firenze" / "accusation.py"

    assert "from firenze.verdict" not in source.read_text(encoding="utf-8")


@pytest.mark.parametrize("locale", ["pt-BR", "en"])
def test_the_summary_speaks_the_match_language(locale: str) -> None:
    summary = summarise(Draft(culprit="sus-1"), _match().case, load(locale))

    assert summary
