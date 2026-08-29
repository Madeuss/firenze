"""Generator, solver and invariant tests.

They run over many seeds on purpose: a seed that passes proves something about
that seed, not about the generator.
"""

import pytest

from mansao.domain import CaseWithSolution, FactKind, Role
from mansao.generation import InvalidCase, generate, solve, validate
from mansao.generation.solver import reachable_facts
from mansao.generation.validation import rn_004_no_overlap

SEEDS = range(1, 41)


@pytest.fixture(scope="module")
def cases() -> list[CaseWithSolution]:
    return [generate(seed=s) for s in SEEDS]


def test_generation_is_deterministic() -> None:
    assert generate(seed=7).model_dump_json() == generate(seed=7).model_dump_json()


def test_different_seeds_produce_different_cases() -> None:
    assert generate(seed=7).case.model_dump_json() != generate(seed=8).case.model_dump_json()


def test_every_generated_case_passes_the_invariants(cases: list[CaseWithSolution]) -> None:
    for full in cases:
        validate(full)


def test_solver_deduces_the_culprit_without_seeing_the_solution(
    cases: list[CaseWithSolution],
) -> None:
    """RN-002: the deduction starts from reachable facts, not from the answer."""
    for full in cases:
        result = solve(full.case)

        assert result.deducible, f"seed {full.case.seed}: {result.failure_reason}"
        assert result.deduced_culprit == full.solution.culprit
        assert result.candidates == (full.solution.culprit,)


def test_rn_001_exactly_one_culprit(cases: list[CaseWithSolution]) -> None:
    for full in cases:
        suspects = [c.id for c in full.case.cast if c.role is Role.suspect]

        assert full.solution.culprit in suspects
        assert len([c for c in full.case.cast if c.role is Role.victim]) == 1


def test_rn_003_every_innocent_has_a_secret(cases: list[CaseWithSolution]) -> None:
    for full in cases:
        innocents = {
            c.id for c in full.case.cast if c.role is Role.suspect and c.id != full.solution.culprit
        }
        with_secret = {f.exposes_secret_of for f in full.case.facts if f.kind is FactKind.secret}

        assert innocents <= with_secret


def test_rn_004_catches_a_planted_overlap() -> None:
    """The validator has to fail on a broken case, not only pass on a good one."""
    full = generate(seed=3)
    presence = next(f for f in full.case.facts if f.kind is FactKind.presence)
    assert presence.room is not None
    other_room = next(r for r in full.case.rooms if r != presence.room)
    tampered = full.model_copy(
        update={
            "case": full.case.model_copy(
                update={
                    "facts": (
                        *full.case.facts,
                        presence.model_copy(update={"id": "F-999", "room": other_room}),
                    )
                }
            )
        }
    )

    with pytest.raises(InvalidCase) as raised:
        rn_004_no_overlap(tampered)

    assert raised.value.rule == "RN-004"


def test_rn_010_dossier_respects_scope(cases: list[CaseWithSolution]) -> None:
    for full in cases:
        for suspect in full.case.suspects:
            for fact in full.case.dossier(suspect.id):
                assert fact.scope.includes(suspect.id)


def test_rn_011_the_case_does_not_carry_the_solution(cases: list[CaseWithSolution]) -> None:
    for full in cases:
        serialised = full.case.model_dump_json()

        assert "culprit" not in serialised
        assert full.solution.motive_key not in serialised


def test_rn_012_restricted_facts_carry_a_canary(cases: list[CaseWithSolution]) -> None:
    for full in cases:
        for fact in full.case.facts:
            if not fact.scope.public:
                assert fact.canary and fact.canary.startswith("CN-")


def test_the_culprit_has_no_reachable_alibi(cases: list[CaseWithSolution]) -> None:
    """The core of the puzzle: every innocent is cleared, the culprit is not."""
    for full in cases:
        case = full.case
        alibied = {
            f.character
            for f in reachable_facts(case)
            if f.kind is FactKind.presence
            and f.interval == case.crime_interval
            and f.room != case.crime_room
        }

        assert full.solution.culprit not in alibied
        assert alibied == {s.id for s in case.suspects} - {full.solution.culprit}


def test_one_innocents_secret_does_not_leak_into_anothers_dossier(
    cases: list[CaseWithSolution],
) -> None:
    """RN-010 where it matters most: the neighbour's dossier."""
    for full in cases:
        for fact in full.case.facts:
            if fact.kind is not FactKind.secret:
                continue
            for suspect in full.case.suspects:
                if suspect.id != fact.exposes_secret_of:
                    assert fact not in full.case.dossier(suspect.id)


def test_fewer_than_three_suspects_is_refused() -> None:
    with pytest.raises(ValueError, match="3 suspects"):
        generate(seed=1, suspects=2)


@pytest.mark.parametrize("suspects", [3, 4, 5, 7])
def test_casts_of_different_sizes(suspects: int) -> None:
    full = generate(seed=11, suspects=suspects)

    validate(full)
    assert len(full.case.suspects) == suspects
    assert solve(full.case).deduced_culprit == full.solution.culprit
