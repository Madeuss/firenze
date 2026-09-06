"""Finding contradictions without reading prose. (RN-021)

Two statements contradict when they cannot both be true: the same suspect,
the same interval, two different rooms. That is a comparison, and it is one only
because the reply carries the claim as fields rather than as a sentence.

The alternative would be parsing what a character said, in every language the
game speaks, for a rule that has to hold exactly. ADR-0005 already found that
keeping structure out of prose paid twice; this is the third time.

**A contradiction is not always a fault.** An NPC caught out by evidence changes
their story, and that is a game event rather than a bug (RN-021). The detector
reports; deciding what a contradiction means belongs to the turn that produced
it, and to the confrontation mechanic that has not arrived yet.
"""

from pydantic import BaseModel, ConfigDict

from firenze.domain import Statement


class Contradiction(BaseModel):
    """Two statements by one suspect that cannot both be true."""

    model_config = ConfigDict(frozen=True)

    character: str
    interval: int
    earlier_turn: int
    later_turn: int
    earlier_room: str
    later_room: str

    def __str__(self) -> str:
        return (
            f"{self.character} placed themselves in {self.earlier_room} on turn "
            f"{self.earlier_turn} and in {self.later_room} on turn {self.later_turn}, "
            f"both during interval {self.interval}"
        )


def _claims(statements: tuple[Statement, ...]) -> list[Statement]:
    return [s for s in statements if s.claimed_room is not None and s.claimed_interval is not None]


def find(statements: tuple[Statement, ...]) -> tuple[Contradiction, ...]:
    """Every contradiction among these statements, oldest pair first.

    Compares a suspect only against themselves. Two suspects disagreeing is not
    a contradiction — it is the game working.
    """
    found: list[Contradiction] = []
    for character in sorted({s.character for s in statements}):
        said: dict[int, Statement] = {}
        for statement in sorted(
            _claims(tuple(s for s in statements if s.character == character)), key=lambda s: s.turn
        ):
            interval = statement.claimed_interval
            assert interval is not None  # guaranteed by _claims
            earlier = said.get(interval)
            if earlier is not None and earlier.claimed_room != statement.claimed_room:
                found.append(
                    Contradiction(
                        character=character,
                        interval=interval,
                        earlier_turn=earlier.turn,
                        later_turn=statement.turn,
                        earlier_room=str(earlier.claimed_room),
                        later_room=str(statement.claimed_room),
                    )
                )
            else:
                said[interval] = statement
    return tuple(found)


def contradicts(
    claimed_room: str | None,
    claimed_interval: int | None,
    said_before: tuple[Statement, ...],
) -> Contradiction | None:
    """Whether a new claim contradicts something this suspect already said.

    The earliest conflicting claim wins as the anchor: a suspect who has said
    three different things about one hour contradicts the first of them, and
    reporting the most recent pair would hide how long the story has been
    moving.
    """
    if claimed_room is None or claimed_interval is None:
        return None

    for prior in sorted(_claims(said_before), key=lambda s: s.turn):
        if prior.claimed_interval == claimed_interval and prior.claimed_room != claimed_room:
            return Contradiction(
                character=prior.character,
                interval=claimed_interval,
                earlier_turn=prior.turn,
                later_turn=prior.turn + 1,
                earlier_room=str(prior.claimed_room),
                later_room=claimed_room,
            )
    return None
