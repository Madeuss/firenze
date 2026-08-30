"""Deducibility solver.

It takes `Case`, never `CaseWithSolution`: if it could read the answer it would
only prove it can read. The signature is the guarantee. (RN-002, RN-011)

The deduction model: start from the public facts and add everything some
suspect would reveal if asked — a suspect tells the truth about anything that
neither incriminates them nor exposes their secret (RN-020). Over that
reachable set, a case is deducible when exactly one suspect is left without a
confirmed alibi and a physical clue points at them.

It reasons over structure, never over prose: no sentence is parsed here, which
is why the same solver works in every locale (ADR-0005).
"""

from pydantic import BaseModel, ConfigDict

from firenze.domain import Case, Fact, FactKind


class SolverResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    deducible: bool
    deduced_culprit: str | None
    candidates: tuple[str, ...]
    chain: tuple[str, ...]
    failure_reason: str | None = None


def will_tell_truth(case: Case, suspect: str, fact: Fact) -> bool:
    """A suspect lies only about what incriminates them or exposes their secret. (RN-020)"""
    if fact.exposes_secret_of == suspect:
        return False
    if fact.incriminates == suspect:
        return False
    incriminating_presence = (
        fact.kind is FactKind.presence
        and fact.character == suspect
        and fact.room == case.crime_room
        and fact.interval == case.crime_interval
    )
    return not incriminating_presence


def reachable_facts(case: Case) -> tuple[Fact, ...]:
    """Public facts plus everything someone would reveal when asked.

    One pass is enough: today, willingness to reveal does not depend on what
    the player already knows. When confrontation unlocks facts (phase 4), this
    becomes a fixpoint.
    """
    reachable: dict[str, Fact] = {f.id: f for f in case.facts if f.scope.public}
    for suspect in case.suspects:
        for fact in case.dossier(suspect.id):
            if fact.id not in reachable and will_tell_truth(case, suspect.id, fact):
                reachable[fact.id] = fact
    return tuple(reachable.values())


def _is_alibi(fact: Fact, case: Case) -> bool:
    return (
        fact.kind is FactKind.presence
        and fact.interval == case.crime_interval
        and fact.room != case.crime_room
        and fact.witness is not None
        and fact.witness != fact.character
    )


def solve(case: Case) -> SolverResult:
    reachable = reachable_facts(case)

    alibis: dict[str, str] = {
        f.character: f.id for f in reachable if f.character is not None and _is_alibi(f, case)
    }
    candidates = tuple(s.id for s in case.suspects if s.id not in alibis)

    if len(candidates) != 1:
        return SolverResult(
            deducible=False,
            deduced_culprit=None,
            candidates=candidates,
            chain=(),
            failure_reason=(
                "no suspect without an alibi"
                if not candidates
                else f"{len(candidates)} suspects without a confirmed alibi"
            ),
        )

    candidate = candidates[0]
    evidence = tuple(
        f.id for f in reachable if f.kind is FactKind.clue and f.incriminates == candidate
    )
    if not evidence:
        return SolverResult(
            deducible=False,
            deduced_culprit=None,
            candidates=candidates,
            chain=(),
            failure_reason="no reachable physical clue points at the only candidate",
        )

    body = tuple(f.id for f in reachable if f.kind is FactKind.body)
    return SolverResult(
        deducible=True,
        deduced_culprit=candidate,
        candidates=candidates,
        chain=body + tuple(sorted(alibis.values())) + evidence,
    )
