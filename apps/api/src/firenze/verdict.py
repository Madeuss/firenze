"""The verdict, computed. (RN-031, RN-032, RN-033)

This module is where the project's loudest claim gets cashed: **the model never
decides the outcome.** Everything here is arithmetic over structured fields, and
a test with a mocked model proves the result does not depend on the model at
all — because no model is reachable from this file.

That is not caution about hallucination. It is that a game whose verdict came
from a language model would be irreproducible and, on a bad day, unfair in a way
nobody could audit. A player who lost deserves to be able to see why.

## What the score is made of (RN-033)

| | Points | How |
|---|---|---|
| The culprit | 50 | All or nothing. There is one right answer. |
| The motive | 20 | All or nothing, and only offered if the player names one. |
| The evidence | 20 | Proportional to how much of the real chain was presented. |
| Turns saved | 10 | Proportional to the budget left when the accusation came. |

The evidence award is proportional rather than all-or-nothing on purpose: a
player who found two of three links reasoned further than one who guessed, and
a scheme that paid them the same would teach guessing.

Naming the culprit and nothing else still scores 50. That is deliberate — the
game rewards being right, and rewards *showing your work* on top.

**The motive is worth points only because it became findable.** It used to be
drawn at random and never planted, so scoring it would have been a lottery
dressed as deduction. It is now a fact with a scope and a witness, and the solver
refuses a case where nobody could reach it (ADR-0011).
"""

from pydantic import BaseModel, ConfigDict, Field

from firenze.domain import Match, Role

CULPRIT_POINTS = 50
MOTIVE_POINTS = 20
EVIDENCE_POINTS = 20
SPEED_POINTS = 10


class Accusation(BaseModel):
    """One per match, irreversible. (RN-031)"""

    model_config = ConfigDict(frozen=True)

    culprit: str
    motive_key: str | None = None
    """Why they did it. Optional: naming nobody's motive is not wrong, it is
    simply unclaimed."""
    evidence: tuple[str, ...] = ()
    """Facts offered in support. Only those the player actually holds count."""


class Verdict(BaseModel):
    """What the accusation was worth, and what was true.

    The truth travels with it because the match is over. This is the one moment
    the solution is a legitimate thing to send to a client (RN-011 governs the
    match, not its ending).
    """

    model_config = ConfigDict(frozen=True)

    correct: bool
    motive_correct: bool
    culprit: str = Field(description="Who actually did it.")
    means_key: str
    motive_key: str

    score: int
    culprit_points: int
    motive_points: int
    evidence_points: int
    speed_points: int

    evidence_expected: tuple[str, ...]
    evidence_offered: tuple[str, ...]
    evidence_hit: tuple[str, ...]


class AlreadyAccused(RuntimeError):
    """RN-031: one accusation per match, and it does not come back."""


class NotASuspect(ValueError):
    """Accusing somebody who is not in the cast is not a wrong answer, it is a typo."""


class NotDecided(RuntimeError):
    """A match still being played has no verdict to recompute."""


def judge(match: Match, accusation: Accusation) -> Verdict:
    """Decide the outcome. Pure: same match and accusation, same verdict."""
    if match.is_over:
        raise AlreadyAccused("this match has already been decided")
    return _decide(match, accusation)


def verdict_of(match: Match) -> Verdict:
    """The verdict of a match that has already been decided.

    A review recomputes the outcome instead of reading a stored copy. The
    arithmetic is a function of the record and the accusation (RN-036), and
    both are on the match — so there is one place the score can come from, and
    a review cannot disagree with the ending the player was shown.

    `judge` refuses a decided match on purpose (RN-031), which is why this does
    not call it.
    """
    if match.accused_culprit is None:
        raise NotDecided("this match has not been accused")
    return _decide(
        match,
        Accusation(
            culprit=match.accused_culprit,
            motive_key=match.accused_motive_key,
            evidence=match.accused_evidence,
        ),
    )


def _decide(match: Match, accusation: Accusation) -> Verdict:
    suspects = {c.id for c in match.case.cast if c.role is Role.suspect}
    if accusation.culprit not in suspects:
        raise NotASuspect(f"{accusation.culprit!r} is not a suspect in this case")

    solution = match.full_case.solution
    correct = accusation.culprit == solution.culprit

    expected = tuple(solution.chain)
    # Only evidence the player actually holds counts. Naming a fact id they were
    # never told is a guess at the shape of the answer, not a deduction.
    offered = tuple(e for e in accusation.evidence if e in match.evidence)
    hit = tuple(e for e in expected if e in offered)

    motive_correct = accusation.motive_key == solution.motive_key
    culprit_points = CULPRIT_POINTS if correct else 0
    # Only alongside the right person: the motive of somebody who did not do it
    # is not half an answer, it is a different story.
    motive_points = MOTIVE_POINTS if correct and motive_correct else 0
    evidence_points = round(EVIDENCE_POINTS * len(hit) / len(expected)) if expected else 0
    speed_points = round(SPEED_POINTS * match.turns_left / _budget(match))

    return Verdict(
        correct=correct,
        motive_correct=motive_correct,
        culprit=solution.culprit,
        means_key=solution.means_key,
        motive_key=solution.motive_key,
        score=culprit_points + motive_points + evidence_points + speed_points,
        culprit_points=culprit_points,
        motive_points=motive_points,
        evidence_points=evidence_points,
        speed_points=speed_points,
        evidence_expected=expected,
        evidence_offered=offered,
        evidence_hit=hit,
    )


def _budget(match: Match) -> int:
    """The budget this match started with, so speed is a fraction of it."""
    default = Match.model_fields["turns_left"].default
    return int(default) if isinstance(default, int) else 30
