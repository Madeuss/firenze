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
    motive = "motive"
    """Why the culprit did it. Held by whoever overheard, never by the house."""


class Intent(StrEnum):
    """What a player was doing when they typed. (RN-040)

    Classified before any suspect sees the message, and `injection` never
    reaches one (RN-041).
    """

    question = "question"
    confrontation = "confrontation"
    meta = "meta"
    injection = "injection"


class Stance(StrEnum):
    """How a suspect is holding up. Transitions are code, never the model's call.

    The model may suggest one; the backend validates it against the machine in
    `firenze.interrogation.stance` and keeps the current stance if the
    suggestion is not a legal move (RN-023). `broken` is absorbing and is only
    reachable by confrontation, which arrives in phase 4.
    """

    cooperative = "cooperative"
    evasive = "evasive"
    hostile = "hostile"
    broken = "broken"


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
    motive_key: str | None = None
    """Message key of the motive, for `kind == motive`.

    The motive used to live only in `Solution`, which made it undiscoverable:
    the player could be told it at the end and had no way to work it out. As a
    fact it has a scope, somebody who can reveal it, and a solver that checks it
    is reachable."""
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
    setting: str
    """Which world the generator built from.

    A seed identifies a case only together with the generator version and the
    setting. The moment a second setting exists, seed 42 means two different
    mysteries — and reproducibility, which is the whole premise of ADR-0004,
    quietly stops holding. Recorded now because adding it after cases are
    persisted is a migration.
    """
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


class Turn(BaseModel):
    """One go, whether or not anybody said anything.

    The record used to hold only answers, which meant a finished match showed
    thirty turns spent and twenty statements, with no account of the other ten.
    A budget that cannot be reconciled is a budget a player cannot trust, and a
    replay that skips the rejections tells a story that did not happen.

    `line` is empty when the turn produced nothing — a leaked canary, a
    contradiction, an unreachable provider. `rejected_by` says which.
    """

    model_config = ConfigDict(frozen=True)

    turn: int
    character: str
    question: str
    line: str = ""
    stance: Stance
    lied: bool = False
    rejected_by: str | None = None
    """Which check discarded the reply, when one did. Empty for an answer."""
    cost: int = 1
    """Turns this cost. A confrontation costs two (RN-030)."""
    fact_referenced: str | None = None
    claimed_room: str | None = None
    """Where they said they were, when the answer said anything about it."""
    claimed_interval: int | None = None
    clue_revealed: str | None = None
    """A fact this answer gave away. How the player comes to hold evidence."""
    intent: Intent = Intent.question
    """How the question was labelled. An `injection` turn is a canned
    deflection: no model was asked, and the record says so."""

    @property
    def answered(self) -> bool:
        return bool(self.line) and self.rejected_by is None


class Match(BaseModel):
    """One playthrough. Holds the solution, because the server has to know it.

    The boundary is not here — it is the dossier. `Match` is what the verdict
    will be computed from (RN-032); `Dossier` is what a model is allowed to see.
    """

    model_config = ConfigDict(frozen=True)

    full_case: CaseWithSolution
    locale: str
    turns_left: int = 30
    stances: dict[str, Stance] = Field(default_factory=dict)
    turns: tuple[Turn, ...] = ()
    """Everything that happened, in order — answers and rejections alike."""
    accused_culprit: str | None = None
    """Set once, never unset. RN-031 makes an accusation irreversible, and the
    cheapest way to keep a rule like that is to have nowhere to put a second
    one."""
    accused_motive_key: str | None = None
    """Why the player said they did it. Kept because the verdict is derived
    rather than stored: without it a review could not reproduce the score it
    already showed."""
    accused_evidence: tuple[str, ...] = ()

    @property
    def is_over(self) -> bool:
        """No more questions after an accusation. The match had its ending."""
        return self.accused_culprit is not None

    @property
    def case(self) -> Case:
        return self.full_case.case

    def stance_of(self, character: str) -> Stance:
        return self.stances.get(character, Stance.cooperative)

    @property
    def statements(self) -> tuple[Turn, ...]:
        """The turns that produced something a character actually said.

        Contradiction detection and the notebook read this; the replay reads
        `turns`. Same record, two questions asked of it.
        """
        return tuple(t for t in self.turns if t.answered)

    def said_by(self, character: str) -> tuple[Turn, ...]:
        return tuple(s for s in self.statements if s.character == character)

    @property
    def evidence(self) -> frozenset[str]:
        """Facts the player is holding, and may confront somebody with.

        Derived rather than stored: it is the public facts plus whatever a
        suspect gave away. A player cannot present what they were never told,
        and there is no second place where that could drift out of agreement
        with the statements it comes from.
        """
        given = {s.clue_revealed for s in self.statements if s.clue_revealed}
        public = {f.id for f in self.case.facts if f.scope.public}
        return frozenset(public | given)
