"""What a suspect is allowed to return.

RN-022 fixes the shape: a line, a stance, whether they lied, and which fact they
leaned on. **Scoring reads the fields, never the line** — which is why the
fields exist at all. A system that scored the prose would have to parse prose,
and would be guessing in every language.

`lied` and `clue_revealed` are the model reporting on itself, so they are
evidence rather than truth: useful for evals and for the notebook, never for the
verdict, which is computed from structure (RN-032).

`claimed_room` and `claimed_interval` are what make RN-021 enforceable. A
contradiction is two statements that cannot both be true — and deciding that by
reading prose would mean parsing prose, in every language, for a rule that has
to hold exactly. Asked for the claim as a room and an interval, the check is a
comparison.
"""

from pydantic import BaseModel, ConfigDict, Field

from firenze.domain import Stance


class NpcReply(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: str = Field(description="What the character says, in character.")
    stance: Stance = Field(
        description="How they are holding up. A suggestion; the backend decides."
    )
    lied: bool = Field(description="Whether this answer contradicts what they know to be true.")
    fact_referenced: str | None = Field(
        default=None, description="Id of the fact this answer leans on, if any."
    )
    clue_revealed: str | None = Field(
        default=None, description="Id of a fact this answer gave away, if any."
    )
    claimed_room: str | None = Field(
        default=None,
        description="If this answer says where you were, the room id. Otherwise nothing.",
    )
    claimed_interval: int | None = Field(
        default=None,
        description="Which interval that claim is about. Required whenever a room is claimed.",
    )
