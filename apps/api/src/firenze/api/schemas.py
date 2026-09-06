"""What crosses the wire.

These are not the domain objects, and the difference is the point. A turn
produces `lied`, `fact_referenced` and `clue_revealed` — bookkeeping the scoring
reads (RN-022) and the prompt itself tells the character are *"not shown to the
detective"*. Returning them would hand the player a lie detector and end the
game on turn one.

So the API has its own models, and what a player may know is decided by which
fields exist here rather than by remembering not to serialise the others.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from firenze.domain import Stance


class NewMatch(BaseModel):
    seed: int = Field(description="Same seed, same mystery.")
    locale: str = Field(default="pt-BR", description="Fixed for the match (ADR-0005).")
    suspects: int = Field(default=6, ge=3, le=8)


class CastMember(BaseModel):
    id: str
    name: str
    role: str
    stance: Stance | None = Field(
        default=None, description="How they are holding up. Absent until they have been asked."
    )


class KnownFact(BaseModel):
    id: str
    text: str


class Said(BaseModel):
    """One line in the notebook, as the player recorded it."""

    turn: int
    character: str
    question: str
    line: str
    stance: Stance


class MatchState(BaseModel):
    """Everything a player may see. No solution, no bookkeeping."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    seed: int
    locale: str
    turns_left: int
    cast: tuple[CastMember, ...]
    known: tuple[KnownFact, ...]
    notebook: tuple[Said, ...]
    evidence: tuple[str, ...] = Field(
        default=(), description="Fact ids the player holds and may present."
    )


class Question(BaseModel):
    suspect: str = Field(description="Character id, e.g. sus-1.")
    question: str = Field(min_length=1, max_length=500)


class Confrontation(BaseModel):
    suspect: str = Field(description="Character id, e.g. sus-1.")
    evidence: str = Field(description="Fact id the player holds, e.g. F-014.")


class Answer(BaseModel):
    """What came back, and what it cost.

    `answered` is false when a reply was produced and then discarded — by the
    output filters, or by the provider declining. The turn is spent, because the
    player had their go.

    An unreachable model is not this shape: it is a 503 and costs nothing.

    `reason` stays coarse on purpose. The detail can quote the canary token the
    reply was discarded for, which is precisely the thing that must not travel.
    """

    model_config = ConfigDict(frozen=True)

    answered: bool
    character: str
    line: str | None = None
    stance: Stance | None = None
    reason: str | None = Field(
        default=None, description="`rejected` or `model_unavailable`, when unanswered."
    )
    alibi_broken: bool = Field(
        default=False,
        description="The evidence caught them out. A game event, not a fault (RN-021).",
    )
    turns_left: int
