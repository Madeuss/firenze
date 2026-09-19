"""Structural invariants of a case.

Each function maps to one numbered rule. They run over the finished case, not
over the intent of whoever produced it — that is what keeps the tests worth
something when the generator changes, or when a case arrives from elsewhere.
"""

from firenze.domain import CaseWithSolution, FactKind, Role


class InvalidCase(ValueError):
    """A case that breaks an integrity rule. Never publishable."""

    def __init__(self, rule: str, detail: str) -> None:
        super().__init__(f"{rule}: {detail}")
        self.rule = rule
        self.detail = detail


def validate(full: CaseWithSolution) -> None:
    """Run every check. Raises `InvalidCase` on the first violation."""
    rn_001_single_culprit(full)
    rn_003_secret_per_innocent(full)
    rn_004_no_overlap(full)
    rn_005_cover_is_not_an_alibi(full)
    rn_012_canary_on_restricted_facts(full)


def rn_001_single_culprit(full: CaseWithSolution) -> None:
    suspects = {c.id for c in full.case.cast if c.role is Role.suspect}
    if full.solution.culprit not in suspects:
        raise InvalidCase("RN-001", f"culprit {full.solution.culprit!r} is not a suspect")


def rn_003_secret_per_innocent(full: CaseWithSolution) -> None:
    innocents = {
        c.id for c in full.case.cast if c.role is Role.suspect and c.id != full.solution.culprit
    }
    with_secret = {f.exposes_secret_of for f in full.case.facts if f.kind is FactKind.secret}
    missing = innocents - with_secret
    if missing:
        raise InvalidCase("RN-003", f"innocents without a secret of their own: {sorted(missing)}")


def rn_004_no_overlap(full: CaseWithSolution) -> None:
    """Nobody in two rooms in the same interval.

    The culprit's cover story is exempt, and that is the rule working rather
    than bending: RN-004 is about where people were, and a cover is about where
    somebody says they were. Reading a lie as a position would make every case
    with a culprit who talks invalid.
    """
    where: dict[tuple[str, int], str] = {}
    for fact in full.case.facts:
        if fact.kind is FactKind.cover:
            continue
        if fact.character is None or fact.room is None or fact.interval is None:
            continue
        slot = (fact.character, fact.interval)
        previous = where.setdefault(slot, fact.room)
        if previous != fact.room:
            raise InvalidCase(
                "RN-004",
                f"{fact.character} appears in {previous} and in {fact.room} "
                f"during interval {fact.interval}",
            )


def rn_005_cover_is_not_an_alibi(full: CaseWithSolution) -> None:
    """The culprit has a version, and it can never clear them.

    Three ways it could, all closed here: naming a witness would make the
    solver read it as an alibi and leave the case with no candidate; naming the
    crime room would confess; belonging to anyone but the culprit would put a
    lie in an innocent's mouth.
    """
    covers = [f for f in full.case.facts if f.kind is FactKind.cover]
    if len(covers) != 1:
        raise InvalidCase("RN-005", f"expected exactly one cover story, found {len(covers)}")

    cover = covers[0]
    if cover.character != full.solution.culprit:
        raise InvalidCase("RN-005", f"the cover story belongs to {cover.character!r}")
    if cover.witness is not None:
        raise InvalidCase("RN-005", "a cover story with a witness would read as an alibi")
    if cover.room == full.case.crime_room:
        raise InvalidCase("RN-005", "the cover story names the crime room")
    if cover.interval != full.case.crime_interval:
        raise InvalidCase("RN-005", "the cover story is not about the hour of the crime")
    if cover.scope.public or cover.scope.characters != {full.solution.culprit}:
        raise InvalidCase("RN-005", "the cover story is visible to somebody else")


def rn_012_canary_on_restricted_facts(full: CaseWithSolution) -> None:
    """Every non-public fact carries a canary."""
    without = [f.id for f in full.case.facts if not f.scope.public and not f.canary]
    if without:
        raise InvalidCase("RN-012", f"restricted facts without a canary: {without}")
