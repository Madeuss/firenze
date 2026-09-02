"""The boundary between what the server knows and what a model may see.

`Match` holds the solution — it has to, because the verdict is computed from it
(RN-032). This module is the one place allowed to read it, and what comes out
the other side is a `Dossier`: one suspect's facts, plus one bit about
themselves.

That bit exists because of a gap the case model does not otherwise fill. The
culprit was alone with the victim, so no presence fact was ever written about
them at that hour, and nothing in their own dossier incriminates them. Without
being told, a culprit is indistinguishable from an innocent who happens to lack
an alibi — they would answer with the same easy conscience, and the mystery
would have no centre.

RN-011 anticipates exactly this: the `Solution` entity never enters a suspect's
context, but *"o culpado sabe apenas da própria culpa"*. So `is_culprit` crosses
the boundary and nothing else does. A suspect learns whether they did it, never
who else might have, never the means, never the motive, never the chain.
"""

from pydantic import BaseModel, ConfigDict

from firenze.domain import Fact, Match, Stance, Statement


class Dossier(BaseModel):
    """Everything one suspect knows, and nothing else.

    This is the type the prompt builder takes. It cannot reach another suspect's
    secret, the solution, or the deduction chain, because it does not carry
    them (RN-010, RN-011).
    """

    model_config = ConfigDict(frozen=True)

    character: str
    name: str
    is_culprit: bool
    """Only ever true for the one suspect it is true of."""
    stance: Stance
    facts: tuple[Fact, ...]
    said_before: tuple[Statement, ...]
    """Their own past statements. RN-021 compares a suspect against themselves."""


def build(match: Match, character: str) -> Dossier:
    """Project the match down to one suspect's view of the night."""
    case = match.case
    known = {c.id for c in case.suspects}
    if character not in known:
        raise KeyError(f"{character!r} is not a suspect in this case")

    return Dossier(
        character=character,
        name=case.name_of(character),
        is_culprit=match.full_case.solution.culprit == character,
        stance=match.stance_of(character),
        facts=case.dossier(character),
        said_before=match.said_by(character),
    )
