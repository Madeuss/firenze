"""Confrontation tests. (RN-021, RN-023, RN-030)

The claim these protect: whether evidence lands is decided by code, and the
model only writes the reaction. Every test that matters here asserts an outcome
the model was never asked about.
"""

from typing import Any

import pytest

from firenze.domain import FactKind, Intent, Match, Stance, Turn
from firenze.generation import generate
from firenze.i18n import load
from firenze.interrogation import COST, NoTurnsLeft, UnknownEvidence, ask, confront, weigh
from firenze.interrogation.models import NpcReply
from firenze.safety import Classification


def _match() -> Match:
    return Match(full_case=generate(seed=42), locale="pt-BR")


def _said(turn: int, character: str, room: str, interval: int) -> Turn:
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


class Reacting:
    """A suspect that answers, and always suggests staying cooperative."""

    def __init__(self, line: str = "Não sei o que dizer, senhor.") -> None:
        self._line = line
        self.prompts: list[str] = []

    @property
    def name(self) -> str:
        return "reacting"

    def complete(self, **kwargs: Any) -> Any:
        if kwargs["schema"] is Classification:
            return Classification(intent=Intent.question, reason="a question")
        self.prompts.append(kwargs["system"])
        return NpcReply(line=self._line, stance=Stance.cooperative, lied=False)


# --- what the evidence does, decided by code ------------------------------


def test_evidence_that_puts_them_elsewhere_breaks_the_alibi() -> None:
    case = generate(seed=42).case
    presence = next(f for f in case.facts if f.kind is FactKind.presence and f.character == "sus-1")
    assert presence.room is not None and presence.interval is not None
    elsewhere = next(r for r in case.rooms if r != presence.room)

    landed = weigh(presence, (_said(1, "sus-1", elsewhere, presence.interval),), case)

    assert landed.breaks_alibi
    assert landed.claimed_room == elsewhere
    assert landed.evidence_room == presence.room


def test_evidence_that_agrees_with_them_breaks_nothing() -> None:
    case = generate(seed=42).case
    presence = next(f for f in case.facts if f.kind is FactKind.presence and f.character == "sus-1")
    assert presence.room is not None and presence.interval is not None

    landed = weigh(presence, (_said(1, "sus-1", presence.room, presence.interval),), case)

    assert not landed.breaks_alibi


def test_evidence_about_somebody_else_does_not_catch_this_suspect() -> None:
    """Uncomfortable to be shown, and not a contradiction of anything they said."""
    case = generate(seed=42).case
    other = next(f for f in case.facts if f.kind is FactKind.presence and f.character == "sus-2")
    assert other.room is not None and other.interval is not None
    elsewhere = next(r for r in case.rooms if r != other.room)

    landed = weigh(other, (_said(1, "sus-1", elsewhere, other.interval),), case)

    assert not landed.breaks_alibi


def test_a_suspect_who_claimed_nothing_cannot_be_caught_out() -> None:
    case = generate(seed=42).case
    presence = next(f for f in case.facts if f.kind is FactKind.presence)

    assert not weigh(presence, (), case).breaks_alibi


# --- the turn -------------------------------------------------------------


def test_a_confrontation_costs_two_turns() -> None:
    """RN-030. Evidence is scarce and the budget is the pacing."""
    match = _match()

    result = confront(match, "sus-1", "F-001", catalog=load("pt-BR"), model=Reacting())

    assert result.match.turns_left == match.turns_left - COST


def test_evidence_the_player_does_not_hold_is_refused() -> None:
    """A player cannot present what they were never told."""
    match = _match()
    unheld = next(f.id for f in match.case.facts if f.id not in match.evidence)

    with pytest.raises(UnknownEvidence):
        confront(match, "sus-1", unheld, catalog=load("pt-BR"), model=Reacting())


def test_the_budget_has_to_cover_the_whole_cost() -> None:
    match = _match().model_copy(update={"turns_left": 1})

    with pytest.raises(NoTurnsLeft, match="costs 2"):
        confront(match, "sus-1", "F-001", catalog=load("pt-BR"), model=Reacting())


def test_a_landed_confrontation_breaks_the_stance_whatever_the_model_suggests() -> None:
    """RN-023: `broken` is reachable only from here, and never from a suggestion."""
    full = generate(seed=42)
    presence = next(
        f for f in full.case.facts if f.kind is FactKind.presence and f.character == "sus-1"
    )
    assert presence.room is not None and presence.interval is not None
    elsewhere = next(r for r in full.case.rooms if r != presence.room)

    match = Match(
        full_case=full,
        locale="pt-BR",
        turns=(_said(1, "sus-1", elsewhere, presence.interval),),
    ).model_copy(update={"stances": {"sus-1": Stance.evasive}})
    holding = match.model_copy(update={"turns": (*match.turns, _revealing(presence.id))})

    model = Reacting()
    result = confront(holding, "sus-1", presence.id, catalog=load("pt-BR"), model=model)

    assert result.alibi_broken
    assert result.turn.answered
    assert result.turn.stance is Stance.broken, "the model suggested cooperative"
    assert result.stance_overruled


def _revealing(fact_id: str) -> Turn:
    """A statement that handed the player a fact, so they may present it."""
    return Turn(
        turn=2,
        character="sus-3",
        question="e então?",
        line="Vi uma coisa, senhor.",
        stance=Stance.cooperative,
        lied=False,
        clue_revealed=fact_id,
    )


def test_a_confrontation_that_lands_nothing_leaves_the_machine_in_charge() -> None:
    match = _match()

    result = confront(match, "sus-1", "F-001", catalog=load("pt-BR"), model=Reacting())

    assert not result.alibi_broken
    assert result.turn.answered
    assert result.turn.stance is Stance.cooperative


def test_the_confrontation_is_recorded_as_one() -> None:
    result = confront(_match(), "sus-1", "F-001", catalog=load("pt-BR"), model=Reacting())

    assert result.turn.answered
    assert result.turn.intent is Intent.confrontation
    assert result.turn.fact_referenced == "F-001"


def test_the_suspect_is_shown_the_evidence_in_words() -> None:
    model = Reacting()

    confront(_match(), "sus-1", "F-001", catalog=load("pt-BR"), model=model)

    assert "showing you something" in model.prompts[-1]
    assert "corpo de" in model.prompts[-1]


def test_an_ordinary_turn_shows_nobody_anything() -> None:
    """The confrontation section is empty unless something is being presented."""
    model = Reacting()

    ask(_match(), "sus-1", "onde você estava?", catalog=load("pt-BR"), model=model)

    assert "showing you something" not in model.prompts[-1]


# --- evidence ------------------------------------------------------------


def test_the_player_starts_holding_only_what_is_public() -> None:
    match = _match()

    assert match.evidence == frozenset({f.id for f in match.case.facts if f.scope.public})


def test_a_revealed_clue_becomes_evidence() -> None:
    """How a player comes to hold anything: somebody gave it away."""
    match = _match()
    secret = next(f for f in match.case.facts if not f.scope.public)

    holding = match.model_copy(update={"turns": (_revealing(secret.id),)})

    assert secret.id in holding.evidence
    assert secret.id not in match.evidence


def test_a_confrontation_is_recorded_at_what_it_cost() -> None:
    """Two turns spent, one row, `cost` two. (RN-030)

    A confrontation is one event, not two, so it is one row — and the row has
    to carry its own price or the record stops adding up to the budget.
    """
    match = _match()

    result = confront(match, "sus-1", "F-001", catalog=load("pt-BR"), model=Reacting())

    assert len(result.match.turns) == 1
    assert result.turn.cost == COST
    assert sum(t.cost for t in result.match.turns) == match.turns_left - result.match.turns_left
