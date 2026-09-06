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
| The culprit | 60 | All or nothing. There is one right answer. |
| The evidence | 30 | Proportional to how much of the real chain was presented. |
| Turns saved | 10 | Proportional to the budget left when the accusation came. |

The evidence award is proportional rather than all-or-nothing on purpose: a
player who found two of three links reasoned further than one who guessed, and
a scheme that paid them the same would teach guessing.

Naming the culprit while presenting nothing still scores 60. That is deliberate
too — the game rewards being right, and rewards *showing your work* on top.
"""

from pydantic import BaseModel, ConfigDict, Field

from firenze.domain import Match, Role

CULPRIT_POINTS = 60
EVIDENCE_POINTS = 30
SPEED_POINTS = 10


class Accusation(BaseModel):
    """One per match, irreversible. (RN-031)"""

    model_config = ConfigDict(frozen=True)

    culprit: str
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
    culprit: str = Field(description="Who actually did it.")
    means_key: str
    motive_key: str

    score: int
    culprit_points: int
    evidence_points: int
    speed_points: int

    evidence_expected: tuple[str, ...]
    evidence_offered: tuple[str, ...]
    evidence_hit: tuple[str, ...]


class AlreadyAccused(RuntimeError):
    """RN-031: one accusation per match, and it does not come back."""


class NotASuspect(ValueError):
    """Accusing somebody who is not in the cast is not a wrong answer, it is a typo."""


def judge(match: Match, accusation: Accusation) -> Verdict:
    """Decide the outcome. Pure: same match and accusation, same verdict."""
    if match.is_over:
        raise AlreadyAccused("this match has already been decided")

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

    culprit_points = CULPRIT_POINTS if correct else 0
    evidence_points = round(EVIDENCE_POINTS * len(hit) / len(expected)) if expected else 0
    speed_points = round(SPEED_POINTS * match.turns_left / _budget(match))

    return Verdict(
        correct=correct,
        culprit=solution.culprit,
        means_key=solution.means_key,
        motive_key=solution.motive_key,
        score=culprit_points + evidence_points + speed_points,
        culprit_points=culprit_points,
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
