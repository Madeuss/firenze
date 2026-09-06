"""Narration tests. (RN-032)

The property under test is an ordering one: the verdict is finished before any
model is asked anything, so nothing a model does can move it. Most of these
check that a failure changes only the prose.
"""

from typing import Any

import pytest

from firenze.domain import Match, Stance, Statement
from firenze.generation import generate
from firenze.i18n import load
from firenze.model import ModelRefused, ModelUnavailable
from firenze.narration import Epilogue, NarrationRejected, check, render, write
from firenze.verdict import Accusation, judge


def _match(turns_left: int = 10) -> Match:
    return Match(full_case=generate(seed=42), locale="pt-BR", turns_left=turns_left)


def _verdict(correct: bool = True) -> Any:
    match = _match()
    culprit = match.full_case.solution.culprit
    who = culprit if correct else next(s.id for s in match.case.suspects if s.id != culprit)
    return judge(match, Accusation(culprit=who)), who


class Writer:
    def __init__(self, text: str = "A casa dormiu mal naquela noite.") -> None:
        self._text = text
        self.prompts: list[str] = []

    @property
    def name(self) -> str:
        return "writer"

    def complete(self, **kwargs: Any) -> Any:
        self.prompts.append(kwargs["system"])
        return Epilogue(text=self._text)


class Broken:
    def __init__(self, failure: Exception) -> None:
        self._failure = failure

    @property
    def name(self) -> str:
        return "broken"

    def complete(self, **kwargs: Any) -> Any:
        raise self._failure


# --- the ordering ---------------------------------------------------------


def test_the_prompt_is_told_the_answer_rather_than_asked_for_it() -> None:
    """A prompt that could be argued into a different verdict would decide verdicts."""
    verdict, accused = _verdict()
    model = Writer()

    write(verdict, accused, _match().case, load("pt-BR"), model=model)

    system = model.prompts[0]
    assert "The culprit was:" in system
    assert "They were:" in system
    assert _match().case.name_of(verdict.culprit) in system


def test_an_unreachable_model_costs_only_the_prose() -> None:
    verdict, accused = _verdict()

    epilogue = write(
        verdict,
        accused,
        _match().case,
        load("pt-BR"),
        model=Broken(ModelUnavailable("no route to host")),
    )

    assert epilogue is None
    assert verdict.correct, "the outcome did not move"
    assert verdict.culprit_points == 50


def test_a_refusal_costs_only_the_prose() -> None:
    verdict, accused = _verdict()

    assert (
        write(verdict, accused, _match().case, load("pt-BR"), model=Broken(ModelRefused("no")))
        is None
    )


def test_a_rejected_epilogue_costs_only_the_prose() -> None:
    verdict, accused = _verdict()

    assert write(verdict, accused, _match().case, load("pt-BR"), model=Writer("   ")) is None


def test_a_good_epilogue_comes_back() -> None:
    verdict, accused = _verdict()

    epilogue = write(verdict, accused, _match().case, load("pt-BR"), model=Writer())

    assert epilogue == "A casa dormiu mal naquela noite."


# --- what is checkable about an ending ------------------------------------


def test_a_canary_in_the_ending_is_rejected() -> None:
    case = _match().case

    with pytest.raises(NarrationRejected, match="canary"):
        check(Epilogue(text="E assim CN-deadbeef terminou."), case)


def test_an_ordinary_sentence_naming_a_suspect_is_accepted() -> None:
    """The check that used to live here rejected this line.

    Flagging capitalised word pairs that are not in the cast reads a
    sentence-initial verb as a first name — "Foi Vitória Belmiro..." — and a
    false positive costs a player the ending of a match they finished. Prose
    defeats that shape of rule, so the rule is gone rather than tuned.
    """
    case = _match().case
    someone = case.name_of("sus-1")

    check(Epilogue(text=f"Foi {someone}, e a casa soube antes do amanhecer."), case)


def test_a_runaway_ending_is_rejected() -> None:
    case = _match().case

    with pytest.raises(NarrationRejected, match="length"):
        check(Epilogue(text="a" * 5000), case)


def test_the_wrong_answer_is_still_told_the_truth() -> None:
    """A mystery with no resolution is worse than a loss."""
    verdict, accused = _verdict(correct=False)
    model = Writer()

    write(verdict, accused, _match().case, load("pt-BR"), model=model)

    assert "errado" in model.prompts[0]
    assert _match().case.name_of(verdict.culprit) in model.prompts[0]


def test_the_epilogue_never_sees_a_dossier() -> None:
    """It is given an outcome, not a case: there is nothing here to leak."""
    match = _match()
    verdict, accused = _verdict()
    model = Writer()

    write(verdict, accused, match.case, load("pt-BR"), model=model)

    system = model.prompts[0]
    for fact in match.case.facts:
        if fact.canary:
            assert fact.canary not in system


def test_a_statement_is_not_needed_to_end_a_match() -> None:
    """A player who accused on turn one still gets an ending."""
    empty = Match(full_case=generate(seed=42), locale="pt-BR")
    assert empty.statements == ()

    verdict = judge(empty, Accusation(culprit=empty.full_case.solution.culprit))

    assert write(verdict, verdict.culprit, empty.case, load("pt-BR"), model=Writer()) is not None


def test_render_needs_no_model_at_all() -> None:
    """Building the prompt is pure; only sending it is not."""
    verdict, accused = _verdict()

    system, user = render(verdict, accused, _match().case, load("pt-BR"))

    assert system and user
    assert isinstance(
        Statement(
            turn=1,
            character="sus-1",
            question="?",
            line="...",
            stance=Stance.cooperative,
            lied=False,
        ),
        Statement,
    )
