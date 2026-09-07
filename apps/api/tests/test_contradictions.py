"""Contradiction tests. (RN-021)

None of these read a sentence. That is the property being protected: the rule
has to hold exactly, in every language the game speaks, and a check that parsed
prose could not promise that.
"""

from typing import Any

import pytest

from firenze.domain import Intent, Match, Stance, Turn
from firenze.generation import generate
from firenze.i18n import load
from firenze.interrogation import ask
from firenze.interrogation.contradictions import contradicts, find
from firenze.interrogation.guard import ReplyRejected, claim_is_about_this_case
from firenze.interrogation.models import NpcReply
from firenze.safety import Classification


def _said(
    turn: int,
    character: str = "sus-1",
    room: str | None = None,
    interval: int | None = None,
) -> Turn:
    return Turn(
        turn=turn,
        character=character,
        question="onde?",
        line="...",
        stance=Stance.cooperative,
        lied=False,
        claimed_room=room,
        claimed_interval=interval,
    )


# --- the detector ---------------------------------------------------------


def test_two_rooms_in_one_interval_contradict() -> None:
    found = find((_said(1, room="kitchen", interval=2), _said(2, room="cellar", interval=2)))

    assert len(found) == 1
    assert found[0].earlier_room == "kitchen"
    assert found[0].later_room == "cellar"
    assert found[0].interval == 2


def test_the_same_room_twice_is_consistency_not_contradiction() -> None:
    assert find((_said(1, room="kitchen", interval=2), _said(2, room="kitchen", interval=2))) == ()


def test_different_intervals_do_not_contradict() -> None:
    """Being in two rooms across an evening is how evenings work."""
    assert find((_said(1, room="kitchen", interval=1), _said(2, room="cellar", interval=3))) == ()


def test_two_suspects_disagreeing_is_the_game_working() -> None:
    """RN-021 compares a suspect against themselves and nobody else."""
    said = (
        _said(1, character="sus-1", room="kitchen", interval=2),
        _said(2, character="sus-2", room="cellar", interval=2),
    )

    assert find(said) == ()


def test_a_statement_that_claims_nothing_cannot_contradict() -> None:
    """Refusing to commit is allowed. It is saying two things that is not."""
    assert find((_said(1, room="kitchen", interval=2), _said(2))) == ()


def test_the_earliest_claim_is_the_anchor() -> None:
    """A story that has moved twice contradicts where it started, not where it was."""
    said = (
        _said(1, room="kitchen", interval=2),
        _said(2, room="cellar", interval=2),
        _said(3, room="library", interval=2),
    )

    found = find(said)

    assert [c.earlier_room for c in found] == ["kitchen", "kitchen"]


def test_a_new_claim_is_checked_against_what_came_before() -> None:
    conflict = contradicts("cellar", 2, (_said(1, room="kitchen", interval=2),))

    assert conflict is not None
    assert "kitchen" in str(conflict)
    assert contradicts("kitchen", 2, (_said(1, room="kitchen", interval=2),)) is None
    assert contradicts(None, None, (_said(1, room="kitchen", interval=2),)) is None


# --- the guard ------------------------------------------------------------


def test_a_room_that_is_not_in_the_case_is_rejected() -> None:
    """An invented room is not a lie the game can reason about."""
    case = generate(seed=42).case
    reply = NpcReply(
        line="Estava no heliporto.",
        stance=Stance.cooperative,
        lied=False,
        claimed_room="helipad",
        claimed_interval=1,
    )

    with pytest.raises(ReplyRejected, match="not a room"):
        claim_is_about_this_case(reply, case)


def test_an_interval_outside_the_night_is_rejected() -> None:
    case = generate(seed=42).case
    reply = NpcReply(
        line="Estava lá às quatro da manhã.",
        stance=Stance.cooperative,
        lied=False,
        claimed_room="kitchen",
        claimed_interval=99,
    )

    with pytest.raises(ReplyRejected, match="outside this night"):
        claim_is_about_this_case(reply, case)


def test_half_a_claim_says_nothing_comparable() -> None:
    case = generate(seed=42).case
    reply = NpcReply(
        line="Estava na cozinha.",
        stance=Stance.cooperative,
        lied=False,
        claimed_room="kitchen",
    )

    with pytest.raises(ReplyRejected, match="nothing comparable"):
        claim_is_about_this_case(reply, case)


# --- the turn -------------------------------------------------------------


class Claiming:
    """A suspect who says where they were, wherever the test tells it to."""

    def __init__(self, room: str, interval: int) -> None:
        self._room = room
        self._interval = interval

    @property
    def name(self) -> str:
        return "claiming"

    def complete(self, **kwargs: Any) -> Any:
        if kwargs["schema"] is Classification:
            return Classification(intent=Intent.question, reason="a question")
        return NpcReply(
            line="Estava lá, senhor.",
            stance=Stance.cooperative,
            lied=False,
            claimed_room=self._room,
            claimed_interval=self._interval,
        )


def test_a_claim_is_recorded_with_the_statement() -> None:
    match = Match(full_case=generate(seed=42), locale="pt-BR")

    result = ask(match, "sus-1", "onde?", catalog=load("pt-BR"), model=Claiming("kitchen", 2))

    assert result.turn.answered
    assert result.turn.claimed_room == "kitchen"
    assert result.turn.claimed_interval == 2


def test_an_unprompted_contradiction_is_discarded() -> None:
    """RN-021. Until confrontation exists, changing the story is a fault."""
    match = Match(full_case=generate(seed=42), locale="pt-BR")
    first = ask(match, "sus-1", "onde?", catalog=load("pt-BR"), model=Claiming("kitchen", 2))

    second = ask(
        first.match, "sus-1", "e às 22h?", catalog=load("pt-BR"), model=Claiming("cellar", 2)
    )

    assert not second.turn.answered
    assert second.rejected_by == "contradiction"
    assert second.contradiction is not None
    assert "kitchen" in second.contradiction
    assert second.match.turns_left == first.match.turns_left - 1, "the turn is still spent"


def test_repeating_the_same_claim_is_fine() -> None:
    match = Match(full_case=generate(seed=42), locale="pt-BR")
    first = ask(match, "sus-1", "onde?", catalog=load("pt-BR"), model=Claiming("kitchen", 2))

    second = ask(
        first.match, "sus-1", "tem certeza?", catalog=load("pt-BR"), model=Claiming("kitchen", 2)
    )

    assert second.turn.answered


def test_the_prompt_shows_the_commitment_not_only_the_sentence() -> None:
    """A model asked to stay consistent needs to see what it committed to."""

    class Watching(Claiming):
        def __init__(self) -> None:
            super().__init__("kitchen", 2)
            self.prompts: list[str] = []

        def complete(self, **kwargs: Any) -> Any:
            if kwargs["schema"] is not Classification:
                self.prompts.append(kwargs["system"])
            return super().complete(**kwargs)

    model = Watching()
    match = Match(full_case=generate(seed=42), locale="pt-BR")
    first = ask(match, "sus-1", "onde?", catalog=load("pt-BR"), model=model)
    ask(first.match, "sus-1", "e depois?", catalog=load("pt-BR"), model=model)

    assert "não se contradiga" in model.prompts[-1]
    assert "cozinha" in model.prompts[-1]
