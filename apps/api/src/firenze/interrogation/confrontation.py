"""Presenting evidence to a suspect. (RN-021, RN-023, RN-030)

A confrontation is not a question with a different prompt. Three things make it
its own act:

**It costs two turns.** Evidence is scarce and the budget is the game's pacing.

**Whether it lands is decided by code.** The evidence either contradicts what
this suspect claimed or it does not, and that is a comparison of structured
fields — the same comparison RN-021 uses, pointed at a fact instead of at
another statement. The model writes the reaction; it does not get to decide
whether it was caught.

**When it lands, the story is allowed to change.** An unprompted contradiction
is a fault and the reply is discarded. A contradiction produced *by* evidence is
`alibi_broken`, which is the mechanic working — the same event, judged by what
caused it.

`broken` is reachable only from here. That is why the stance machine refuses it
from a suggestion: a character breaks because they were caught, never because a
question felt intense.
"""

from pydantic import BaseModel, ConfigDict

from firenze.domain import Case, Fact, FactKind, Statement

COST = 2


class Landed(BaseModel):
    """What a piece of evidence does to what a suspect said."""

    model_config = ConfigDict(frozen=True)

    breaks_alibi: bool
    contradicted_turn: int | None = None
    claimed_room: str | None = None
    evidence_room: str | None = None
    interval: int | None = None


def weigh(evidence: Fact, said_before: tuple[Statement, ...], case: Case) -> Landed:
    """Decide whether this evidence catches this suspect out.

    It does when the fact places them somewhere at an hour they claimed to have
    been somewhere else. Anything vaguer — a fact about another person, about
    nothing in particular — is a fair thing to show them and does not break
    anybody.
    """
    if evidence.interval is None or evidence.room is None:
        return Landed(breaks_alibi=False)

    for said in said_before:
        if said.claimed_interval != evidence.interval or said.claimed_room is None:
            continue
        if said.claimed_room != evidence.room and _is_about(evidence, said.character, case):
            return Landed(
                breaks_alibi=True,
                contradicted_turn=said.turn,
                claimed_room=said.claimed_room,
                evidence_room=evidence.room,
                interval=evidence.interval,
            )
    return Landed(breaks_alibi=False)


def _is_about(evidence: Fact, character: str, case: Case) -> bool:
    """Whether this fact says something about where *this* suspect was.

    A clue names the owner of the object as its subject, and a presence fact
    names whoever it places. Evidence about somebody else is not a
    contradiction of this suspect, however uncomfortable it is to be shown.
    """
    del case  # kept for signature stability while fact kinds grow
    if evidence.kind is FactKind.presence:
        return evidence.character == character
    if evidence.kind is FactKind.clue:
        return evidence.incriminates == character or evidence.character == character
    return False
