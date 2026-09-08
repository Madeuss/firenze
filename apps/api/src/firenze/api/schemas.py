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


class Room(BaseModel):
    id: str = Field(description="Stable id, e.g. `study`. What a claim names.")
    name: str = Field(description="How to write it in this match's language.")


class Hour(BaseModel):
    interval: int = Field(description="Index into the night, 0-based.")
    label: str = Field(description="Clock time, e.g. `22h30`.")


class FloorPlan(BaseModel):
    """The empty board the player fills in, and nothing else.

    Rooms and hours — never who was where. A server that handed over a filled
    plan would be solving the game: reconstructing the night from what people
    claimed *is* the deduction, so the claims stay in the answers a player has
    to read, and reach the plan only in the review of a finished match (RN-035).

    Neither list is a secret. The rooms are the house and the hours are the
    night; the briefing already says where the body was found.
    """

    model_config = ConfigDict(frozen=True)

    rooms: tuple[Room, ...]
    hours: tuple[Hour, ...]


class Said(BaseModel):
    """One turn in the notebook, whether or not anybody said anything.

    A turn that produced nothing was still charged (RN-030), so it is in the
    notebook the same as the rest. Leaving it out would make the budget
    unexplainable to the player, and would force a front end to keep its own
    copy of what happened — which is a second source for the same truth.

    What it does *not* say is which check discarded the reply. The name of the
    check is information the player did not earn: `contradiction` would tell
    them a suspect contradicted themselves. Same reason `Answer.reason` stays
    coarse.
    """

    turn: int
    character: str
    question: str
    answered: bool
    line: str | None = Field(default=None, description="What they said. Absent when nothing was.")
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
    plan: FloorPlan = Field(description="The house and the night, empty. Constant for the match.")
    notebook: tuple[Said, ...]
    evidence: tuple[str, ...] = Field(
        default=(), description="Fact ids the player holds and may present."
    )
    known_motives: tuple[str, ...] = Field(
        default=(),
        description="Motives the player found out about, and may therefore name.",
    )


class Question(BaseModel):
    suspect: str = Field(description="Character id, e.g. sus-1.")
    question: str = Field(min_length=1, max_length=500)


class Confrontation(BaseModel):
    suspect: str = Field(description="Character id, e.g. sus-1.")
    evidence: str = Field(description="Fact id the player holds, e.g. F-014.")


class AccusationText(BaseModel):
    """What a player typed, before it is a form."""

    text: str = Field(min_length=1, max_length=1000)


class DraftAccusation(BaseModel):
    """The form, filled in from prose, for the player to confirm.

    Nothing here has been committed. `POST /accusation` takes these fields back,
    which is what makes the confirmation structural rather than a convention:
    there is no way to accuse in prose.
    """

    model_config = ConfigDict(frozen=True)

    culprit: str | None = None
    culprit_name: str | None = None
    motive_key: str | None = None
    motive: str | None = None
    evidence: tuple[str, ...] = ()
    evidence_text: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    summary: str = Field(description="The sentence to show before it counts.")


class NewAccusation(BaseModel):
    """One per match, irreversible (RN-031). Choose carefully."""

    culprit: str = Field(description="Character id you are naming.")
    motive_key: str | None = Field(
        default=None, description="Why they did it. Optional — unclaimed is not wrong."
    )
    evidence: tuple[str, ...] = Field(
        default=(), description="Fact ids you offer in support. Only ones you hold count."
    )


class Outcome(BaseModel):
    """The verdict, and the only moment the solution may cross the wire.

    RN-011 governs a match in progress. This is its ending: the player has
    spent their one accusation and is owed the answer, right or wrong.
    """

    model_config = ConfigDict(frozen=True)

    correct: bool
    motive_correct: bool
    accused: str
    culprit: str
    means: str
    motive: str
    score: int
    culprit_points: int
    motive_points: int
    evidence_points: int
    speed_points: int
    evidence_expected: tuple[str, ...]
    evidence_hit: tuple[str, ...]
    turns_left: int
    epilogue: str | None = Field(
        default=None,
        description="How it ended, in prose. Absent when no model could write it — "
        "the verdict above does not depend on it (RN-032).",
    )


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


class ReviewedTurn(BaseModel):
    """One turn as the review shows it: what was asked, and what became of it.

    This carries the bookkeeping `Said` withholds — `lied`, `fact_referenced`,
    `clue_revealed`. It is safe here and nowhere else, for the same reason
    `Outcome` may carry the solution: the match is over. A review of a match
    still being played would be a lie detector, so there is no such thing
    (RN-035).
    """

    model_config = ConfigDict(frozen=True)

    turn: int
    cost: int = Field(description="Turns this one cost. A confrontation costs two (RN-030).")
    character: str
    character_name: str
    question: str
    intent: str = Field(description="How it was classified before anybody answered (RN-040).")
    answered: bool
    line: str | None = Field(default=None, description="What they said. Absent when nothing was.")
    stance: Stance = Field(description="The stance the turn left them in.")
    rejected_by: str | None = Field(
        default=None,
        description="Which check discarded the reply: `canary`, `scope`, `contradiction`, "
        "`refusal`. A name, never the offending text.",
    )
    lied: bool = False
    fact_referenced: str | None = None
    clue_revealed: str | None = Field(
        default=None, description="The fact this answer gave away, if it gave one away."
    )
    claimed_room: str | None = Field(
        default=None, description="Where they said they were. A room id from the plan."
    )
    claimed_interval: int | None = Field(
        default=None, description="When they said it about. An hour index from the plan."
    )


class StanceMove(BaseModel):
    """A suspect changing footing, and the turn that did it."""

    model_config = ConfigDict(frozen=True)

    turn: int
    character: str
    character_name: str
    was: Stance
    became: Stance


class HeldEvidence(BaseModel):
    """A fact the player was holding by the end, and how it got there."""

    model_config = ConfigDict(frozen=True)

    id: str
    text: str
    turn: int | None = Field(
        default=None, description="Absent when it was public from the briefing."
    )
    given_by: str | None = None
    given_by_name: str | None = None


class Review(BaseModel):
    """A finished match, in order, with the budget reconciled.

    `budget`, `turns_left` and the costs in `record` add up, by construction:
    every turn that was charged is a row here, including the ones that produced
    nothing.
    """

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    seed: int
    locale: str
    budget: int
    turns_left: int
    turns_spent: int
    record: tuple[ReviewedTurn, ...]
    stance_trail: tuple[StanceMove, ...]
    evidence_trail: tuple[HeldEvidence, ...]
    outcome: Outcome = Field(
        description="Recomputed from the record, not read from a stored copy (RN-036). "
        "The epilogue is not part of it: prose was never persisted, and its absence "
        "changes nothing about the score."
    )
