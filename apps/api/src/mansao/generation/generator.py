"""Deterministic case generator.

The case structure — culprit, timeline, facts and scopes — is assembled by code
from a seed (ADR-0004). The model only writes the veneer later: names,
personality, scene prose. Same seed and same generator version produce exactly
the same case, which is what makes an eval reproducible.

Nothing here asks the solver how to solve anything; the solver runs at the end
and holds a veto (RN-002).
"""

import hashlib
import random
from itertools import count

from mansao.domain import (
    Case,
    CaseWithSolution,
    Character,
    Fact,
    FactKind,
    Role,
    Scope,
    Solution,
)
from mansao.generation.solver import solve
from mansao.generation.validation import validate

GENERATOR_VERSION = "2"

ROOMS = (
    "library",
    "parlour",
    "dining_room",
    "kitchen",
    "cellar",
    "study",
    "conservatory",
    "basement",
)
DISCREET_ROOMS = ("cellar", "study", "basement")

NIGHT_START_MINUTES = 21 * 60
INTERVAL_MINUTES = 30
INTERVAL_COUNT = 6

# Names are setting, not interface: a Brazilian manor keeps Brazilian names in
# every locale. Translating them would read like bad dubbing.
NAMES = (
    "Aurélio Bastos",
    "Ondina Vilar",
    "Teodoro Mainz",
    "Clarice Antunes",
    "Bartolomeu Sá",
    "Ilma Prado",
    "Nazareno Cruz",
    "Vitória Belmiro",
    "Godofredo Alves",
    "Marlene Tostes",
)
VICTIM_NAME = "Rodolfo Andrade"

MEANS_KEYS = ("bronze_candlestick", "poisoned_decanter", "letter_opener", "curtain_cord")
MOTIVE_KEYS = ("inheritance", "blackmail", "dissolved_partnership", "old_forgery")
SECRET_KEYS = (
    "cellar_wine",
    "reads_the_mail",
    "gambling_debts",
    "secret_meetings",
    "forged_signature",
    "hoarded_objects",
)


class UnsolvableCase(RuntimeError):
    """The generator found no deducible case within its attempt budget."""


def _canary(seed: int, fact_id: str) -> str:
    digest = hashlib.blake2s(f"{seed}:{fact_id}".encode(), digest_size=4).hexdigest()
    return f"CN-{digest}"


def _scope(*characters: str) -> Scope:
    return Scope(public=False, characters=frozenset(characters))


def generate(seed: int, suspects: int = 6, attempts: int = 20) -> CaseWithSolution:
    """Generate a valid, deducible case, or raise `UnsolvableCase`.

    Each attempt uses a derived seed. A rejected case is discarded — loosening
    the check to keep it is the mistake RN-002 exists to prevent.
    """
    if suspects < 3:
        raise ValueError("a case needs at least 3 suspects to have crossed alibis")

    for attempt in range(attempts):
        derived = seed if attempt == 0 else seed * 1000 + attempt
        candidate = _assemble(seed=seed, effective_seed=derived, suspects=suspects)
        validate(candidate)
        if solve(candidate.case).deduced_culprit == candidate.solution.culprit:
            return candidate

    raise UnsolvableCase(f"no deducible case in {attempts} attempts from seed {seed}")


def _assemble(seed: int, effective_seed: int, suspects: int) -> CaseWithSolution:
    rng = random.Random(effective_seed)

    names = list(NAMES)
    rng.shuffle(names)
    cast = (
        Character(id="victim", name=VICTIM_NAME, role=Role.victim),
        *(Character(id=f"sus-{i + 1}", name=names[i], role=Role.suspect) for i in range(suspects)),
    )
    ids = [c.id for c in cast if c.role is Role.suspect]

    crime_room = rng.choice(ROOMS)
    crime_interval = rng.randrange(1, INTERVAL_COUNT - 1)
    culprit = rng.choice(ids)
    innocents = [i for i in ids if i != culprit]

    placement = _place(rng, ids, culprit, innocents, crime_room, crime_interval)
    secrets = _secrets(rng, innocents, crime_interval, placement)

    facts = _facts(
        seed=seed,
        rng=rng,
        ids=ids,
        culprit=culprit,
        innocents=innocents,
        placement=placement,
        secrets=secrets,
        crime_room=crime_room,
        crime_interval=crime_interval,
    )

    case = Case(
        seed=seed,
        generator_version=GENERATOR_VERSION,
        rooms=ROOMS,
        night_start_minutes=NIGHT_START_MINUTES,
        interval_minutes=INTERVAL_MINUTES,
        interval_count=INTERVAL_COUNT,
        cast=cast,
        facts=facts,
        crime_room=crime_room,
        crime_interval=crime_interval,
    )
    solution = Solution(
        culprit=culprit,
        means_key=rng.choice(MEANS_KEYS),
        motive_key=rng.choice(MOTIVE_KEYS),
        chain=tuple(f.id for f in facts if f.kind is FactKind.clue and f.incriminates == culprit),
    )
    return CaseWithSolution(case=case, solution=solution)


def _place(
    rng: random.Random,
    ids: list[str],
    culprit: str,
    innocents: list[str],
    crime_room: str,
    crime_interval: int,
) -> dict[tuple[str, int], str]:
    """Where each suspect was in each interval.

    A mapping from (character, interval) to room makes RN-004 impossible by
    construction — there is no way to be in two places. The validator still
    checks, because a case can be touched after it leaves here.
    """
    placement: dict[tuple[str, int], str] = {}

    # At the time of the crime the culprit is alone with the victim and every
    # innocent has company: that is what leaves exactly one suspect unalibied.
    placement[(culprit, crime_interval)] = crime_room
    available = [r for r in ROOMS if r != crime_room]
    rng.shuffle(available)

    shuffled = list(innocents)
    rng.shuffle(shuffled)
    groups = [shuffled[i : i + 2] for i in range(0, len(shuffled), 2)]
    if len(groups) > 1 and len(groups[-1]) == 1:
        groups[-2].extend(groups.pop())

    for group, room in zip(groups, available, strict=False):
        for cid in group:
            placement[(cid, crime_interval)] = room

    for interval in range(INTERVAL_COUNT):
        if interval == crime_interval:
            continue
        for cid in ids:
            placement[(cid, interval)] = rng.choice(ROOMS)

    return placement


def _secrets(
    rng: random.Random,
    innocents: list[str],
    crime_interval: int,
    placement: dict[tuple[str, int], str],
) -> dict[str, tuple[str, int, str]]:
    """One secret per innocent: room, interval and what it is. (RN-003)

    A secret happens away from the crime and always alone — a secret with a
    witness makes nobody lie.
    """
    secrets: dict[str, tuple[str, int, str]] = {}
    keys = list(SECRET_KEYS)
    rng.shuffle(keys)

    # Distinct (room, interval) pairs. If two secrets landed on the same pair,
    # clearing the room for one would move the other away from their own
    # secret, and the fact would contradict the timeline (RN-004).
    pairs = [
        (room, interval)
        for room in DISCREET_ROOMS
        for interval in range(INTERVAL_COUNT)
        if interval != crime_interval
    ]
    rng.shuffle(pairs)
    if len(pairs) < len(innocents):
        raise ValueError("not enough discreet rooms to give every innocent a secret")

    for cid, key, (room, interval) in zip(innocents, keys, pairs, strict=False):
        secrets[cid] = (room, interval, key)
        placement[(cid, interval)] = room

        elsewhere = rng.choice([r for r in ROOMS if r != room])
        for slot, where in list(placement.items()):
            if slot[1] == interval and slot[0] != cid and where == room:
                placement[slot] = elsewhere

    return secrets


def _facts(
    *,
    seed: int,
    rng: random.Random,
    ids: list[str],
    culprit: str,
    innocents: list[str],
    placement: dict[tuple[str, int], str],
    secrets: dict[str, tuple[str, int, str]],
    crime_room: str,
    crime_interval: int,
) -> tuple[Fact, ...]:
    number = count(1)

    def new_id() -> str:
        return f"F-{next(number):03d}"

    facts: list[Fact] = [
        Fact(
            id=new_id(),
            kind=FactKind.body,
            scope=Scope(public=True),
            room=crime_room,
            interval=crime_interval,
        )
    ]

    # Presence only becomes a fact when someone can attest it. Whoever was
    # alone gets no alibi — and that absence is what the solver looks for.
    for interval in range(INTERVAL_COUNT):
        by_room: dict[str, list[str]] = {}
        for cid in ids:
            by_room.setdefault(placement[(cid, interval)], []).append(cid)

        for room, present in sorted(by_room.items()):
            if len(present) < 2:
                continue
            for i, cid in enumerate(present):
                witness = present[(i + 1) % len(present)]
                fact_id = new_id()
                facts.append(
                    Fact(
                        id=fact_id,
                        kind=FactKind.presence,
                        scope=_scope(cid, witness),
                        character=cid,
                        room=room,
                        interval=interval,
                        witness=witness,
                        canary=_canary(seed, fact_id),
                    )
                )

    for cid, (room, interval, key) in secrets.items():
        fact_id = new_id()
        facts.append(
            Fact(
                id=fact_id,
                kind=FactKind.secret,
                scope=_scope(cid),
                character=cid,
                room=room,
                interval=interval,
                secret_key=key,
                exposes_secret_of=cid,
                canary=_canary(seed, fact_id),
            )
        )

    # The clue. Whoever found it has no reason to hide it, so it is reachable
    # by questioning — the step that closes the deduction. The fact is about
    # the owner of the object; naming the finder here would put an innocent at
    # the murder scene and break the timeline (RN-004).
    finder = rng.choice(innocents)
    fact_id = new_id()
    facts.append(
        Fact(
            id=fact_id,
            kind=FactKind.clue,
            scope=_scope(finder),
            character=culprit,
            room=crime_room,
            interval=crime_interval,
            witness=finder,
            incriminates=culprit,
            canary=_canary(seed, fact_id),
        )
    )

    return tuple(facts)
