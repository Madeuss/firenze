"""Verdict tests. (RN-031, RN-032, RN-033)

Not one of these mentions a model, and that is the assertion. `firenze.verdict`
cannot reach one — the import would have nowhere to come from — so "the outcome
does not depend on the model" is a property of the module rather than a promise
about it.
"""

import pytest

from firenze.domain import Match, Stance, Statement
from firenze.generation import generate
from firenze.verdict import (
    CULPRIT_POINTS,
    EVIDENCE_POINTS,
    SPEED_POINTS,
    Accusation,
    AlreadyAccused,
    NotASuspect,
    judge,
)


def _match(turns_left: int = 30, holding: tuple[str, ...] = ()) -> Match:
    """A match where the player holds whatever the test says they hold."""
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
    return Match(
        full_case=generate(seed=42), locale="pt-BR", turns_left=turns_left, statements=given
    )


def _culprit() -> str:
    return generate(seed=42).solution.culprit


def _chain() -> tuple[str, ...]:
    return tuple(generate(seed=42).solution.chain)


# --- being right ----------------------------------------------------------


def test_naming_the_culprit_is_worth_sixty() -> None:
    verdict = judge(_match(turns_left=0), Accusation(culprit=_culprit()))

    assert verdict.correct
    assert verdict.culprit_points == CULPRIT_POINTS


def test_naming_the_wrong_person_is_worth_nothing_for_that_part() -> None:
    innocent = next(s.id for s in _match().case.suspects if s.id != _culprit())

    verdict = judge(_match(turns_left=0), Accusation(culprit=innocent))

    assert not verdict.correct
    assert verdict.culprit_points == 0
    assert verdict.culprit == _culprit(), "the truth comes back either way"


def test_accusing_somebody_who_is_not_in_the_case_is_a_typo_not_an_answer() -> None:
    with pytest.raises(NotASuspect):
        judge(_match(), Accusation(culprit="sus-99"))


# --- the evidence ---------------------------------------------------------


def test_the_evidence_award_is_proportional() -> None:
    """Two of three links reasoned further than one, and the score says so."""
    chain = _chain()
    match = _match(turns_left=0, holding=chain)

    whole = judge(match, Accusation(culprit=_culprit(), evidence=chain))
    none = judge(match, Accusation(culprit=_culprit(), evidence=()))

    assert whole.evidence_points == EVIDENCE_POINTS
    assert none.evidence_points == 0


def test_only_evidence_the_player_holds_counts() -> None:
    """Naming a fact id they were never told is a guess at the shape of the answer."""
    chain = _chain()
    empty_handed = _match(turns_left=0)

    verdict = judge(empty_handed, Accusation(culprit=_culprit(), evidence=chain))

    assert verdict.evidence_offered == ()
    assert verdict.evidence_points == 0


def test_offering_evidence_that_is_not_part_of_the_chain_earns_nothing() -> None:
    match = _match(turns_left=0, holding=("F-001",))

    verdict = judge(match, Accusation(culprit=_culprit(), evidence=("F-001",)))

    assert "F-001" in verdict.evidence_offered
    assert "F-001" not in verdict.evidence_hit


def test_being_right_with_no_evidence_still_scores() -> None:
    """The game rewards being right, and rewards showing your work on top."""
    verdict = judge(_match(turns_left=0), Accusation(culprit=_culprit()))

    assert verdict.score == CULPRIT_POINTS


# --- the clock ------------------------------------------------------------


def test_turns_saved_are_worth_up_to_ten() -> None:
    untouched = judge(_match(turns_left=30), Accusation(culprit=_culprit()))
    exhausted = judge(_match(turns_left=0), Accusation(culprit=_culprit()))
    halfway = judge(_match(turns_left=15), Accusation(culprit=_culprit()))

    assert untouched.speed_points == SPEED_POINTS
    assert exhausted.speed_points == 0
    assert halfway.speed_points == SPEED_POINTS // 2


def test_a_perfect_match_scores_a_hundred() -> None:
    chain = _chain()

    verdict = judge(
        _match(turns_left=30, holding=chain), Accusation(culprit=_culprit(), evidence=chain)
    )

    assert verdict.score == 100


# --- one accusation, and then it is over ----------------------------------


def test_a_match_can_only_be_decided_once() -> None:
    """RN-031. The cheapest way to keep a rule like that is nowhere to put a second."""
    decided = _match().model_copy(update={"accused_culprit": _culprit()})

    with pytest.raises(AlreadyAccused):
        judge(decided, Accusation(culprit=_culprit()))


def test_an_accusation_ends_the_match() -> None:
    match = _match()

    assert not match.is_over
    assert match.model_copy(update={"accused_culprit": "sus-1"}).is_over


def test_the_verdict_is_the_same_every_time() -> None:
    """RN-032: arithmetic over structured fields, not a judgement call."""
    match = _match(turns_left=7, holding=_chain())
    accusation = Accusation(culprit=_culprit(), evidence=_chain())

    assert judge(match, accusation) == judge(match, accusation)


def test_nothing_in_this_module_can_reach_a_model() -> None:
    """The strongest version of RN-032 available: it is not reachable from here."""
    import pathlib
    import re

    source = pathlib.Path(__file__).resolve().parents[1] / "src" / "firenze" / "verdict.py"
    text = source.read_text(encoding="utf-8")

    assert not re.search(r"^\s*(?:import|from)\s+firenze\.model", text, re.MULTILINE)
    assert "StructuredModel" not in text
