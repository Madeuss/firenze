"""Case entities.

Two rules shape this module.

`Solution` is a separate entity from `Case`, so isolation becomes a function
signature rather than the discipline of whoever writes the next function: code
that builds an NPC's context takes `Case` and cannot reach the culprit (RN-011).

Nothing here holds a rendered sentence. A fact carries a kind and slots — who,
which room, which interval — and prose is produced at the edge, per locale,
from a message catalog (ADR-0005). Rooms are stable ids, never display names;
intervals are indices over a clock the case defines in minutes. Grammar lives
in the catalog, where it can differ per language, not in the data.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    victim = "victim"
    suspect = "suspect"


class FactKind(StrEnum):
    body = "body"
    """Where and when the body was found. Always public."""
    presence = "presence"
    """Who was in which room, in which interval, attested by whom."""
    clue = "clue"
    """A physical object placing someone at a place and time."""
    secret = "secret"
    """A suspect's private secret. A reason to lie without being the culprit."""


class Character(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    role: Role


class Scope(BaseModel):
    """Who is allowed to know a fact. (RN-010)"""

    model_config = ConfigDict(frozen=True)

    public: bool = False
    characters: frozenset[str] = frozenset()

    def includes(self, character: str) -> bool:
        return self.public or character in self.characters


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: FactKind
    scope: Scope

    character: str | None = None
    """Who the fact is about."""
    room: str | None = None
    """Stable room id, resolved to a display name by the catalog."""
    interval: int | None = None
    """Index into the case clock, not a formatted time."""
    witness: str | None = None
    """Who can attest the fact besides the character it is about."""
    secret_key: str | None = None
    """Message key of the secret's text, for `kind == secret`."""
    exposes_secret_of: str | None = None
    """When set, that suspect lies about this fact. (RN-020)"""
    incriminates: str | None = None
    """When set, the fact ties that suspect to the crime."""
    canary: str | None = None
    """Unique token on any non-public fact. A canary in the output is a
    critical failure. (RN-012)"""


class Case(BaseModel):
    """What may circulate through the system. Holds no solution."""

    model_config = ConfigDict(frozen=True)

    seed: int
    generator_version: str
    rooms: tuple[str, ...]
    night_start_minutes: int
    """Minutes since midnight for interval 0. The edge formats it."""
    interval_minutes: int
    interval_count: int
    cast: tuple[Character, ...]
    facts: tuple[Fact, ...]
    crime_room: str
    crime_interval: int

    @property
    def suspects(self) -> tuple[Character, ...]:
        return tuple(c for c in self.cast if c.role is Role.suspect)

    def dossier(self, character: str) -> tuple[Fact, ...]:
        """Facts visible to one character. (RN-010)"""
        return tuple(f for f in self.facts if f.scope.includes(character))

    def name_of(self, character_id: str) -> str:
        for c in self.cast:
            if c.id == character_id:
                return c.name
        raise KeyError(character_id)

    def minutes_at(self, interval: int) -> int:
        return (self.night_start_minutes + interval * self.interval_minutes) % (24 * 60)

    def fact(self, fact_id: str) -> Fact:
        for f in self.facts:
            if f.id == fact_id:
                return f
        raise KeyError(fact_id)


class Solution(BaseModel):
    """Never enters a suspect's context. (RN-011)"""

    model_config = ConfigDict(frozen=True)

    culprit: str
    means_key: str
    motive_key: str
    chain: tuple[str, ...] = Field(default=())
    """Ids of the facts that prove the culprit, in the order they chain."""


class CaseWithSolution(BaseModel):
    """Case plus solution. Only the generator, the solver and the verdict see this."""

    model_config = ConfigDict(frozen=True)

    case: Case
    solution: Solution
