"""Interrogation tests.

None of these need a key. The model is replaced by one that returns exactly the
reply a test needs — which is the point, because the replies worth testing are
the ones a real model produces rarely and that must never reach a player.
"""

from typing import Any

import pytest

from firenze.domain import Match, Stance
from firenze.generation import generate
from firenze.i18n import load
from firenze.interrogation import Dossier, NpcReply, ReplyRejected, ask, build
from firenze.interrogation import stance as stance_machine
from firenze.interrogation.guard import check
from firenze.interrogation.turn import NoTurnsLeft, render
from firenze.model import FakeModel, ModelUnavailable


class Scripted:
    def __init__(self, reply: NpcReply | None = None, failure: Exception | None = None) -> None:
        self._reply = reply
        self._failure = failure
        self.prompts: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "scripted"

    def complete(self, **kwargs: Any) -> Any:
        self.prompts.append(kwargs)
        if self._failure is not None:
            raise self._failure
        return self._reply


@pytest.fixture(scope="module")
def match() -> Match:
    return Match(full_case=generate(seed=42), locale="pt-BR")


@pytest.fixture(scope="module")
def culprit(match: Match) -> str:
    return match.full_case.solution.culprit


def _reply(**overrides: Any) -> NpcReply:
    base: dict[str, Any] = {
        "line": "Eu estava na cozinha, senhor.",
        "stance": Stance.cooperative,
        "lied": False,
    }
    return NpcReply(**{**base, **overrides})


# --- the dossier boundary -------------------------------------------------


def test_a_dossier_carries_only_that_suspects_facts(match: Match) -> None:
    """RN-010, at the point where it decides what a model can possibly say."""
    for suspect in match.case.suspects:
        dossier = build(match, suspect.id)

        for fact in dossier.facts:
            assert fact.scope.includes(suspect.id)


def test_only_the_culprit_is_told_they_are_the_culprit(match: Match, culprit: str) -> None:
    """RN-011: the Solution stays out; one bit about oneself crosses."""
    flagged = [s.id for s in match.case.suspects if build(match, s.id).is_culprit]

    assert flagged == [culprit]


def test_a_dossier_carries_nothing_else_from_the_solution(match: Match, culprit: str) -> None:
    serialised = build(match, culprit).model_dump_json()
    solution = match.full_case.solution

    assert solution.means_key not in serialised
    assert solution.motive_key not in serialised
    for fact_id in solution.chain:
        assert fact_id not in serialised


def test_asking_about_someone_who_is_not_in_the_case(match: Match) -> None:
    with pytest.raises(KeyError):
        build(match, "sus-999")


# --- the prompt -----------------------------------------------------------


def test_the_prompt_never_mentions_another_suspects_secret(match: Match) -> None:
    catalog = load("pt-BR")

    for suspect in match.case.suspects:
        dossier = build(match, suspect.id)
        system, _ = render(dossier, catalog, match, "onde você estava?")

        for fact in match.case.facts:
            if fact.scope.includes(suspect.id):
                continue
            assert fact.id not in system
            if fact.canary:
                assert fact.canary not in system


def test_the_guilt_line_appears_for_exactly_one_suspect(match: Match, culprit: str) -> None:
    catalog = load("pt-BR")
    told = [
        s.id
        for s in match.case.suspects
        if "Você matou" in render(build(match, s.id), catalog, match, "?")[0]
    ]

    assert told == [culprit]


# --- the stance machine ---------------------------------------------------


@pytest.mark.parametrize(
    ("current", "suggested", "expected"),
    [
        (Stance.cooperative, Stance.evasive, Stance.evasive),
        (Stance.evasive, Stance.hostile, Stance.hostile),
        (Stance.hostile, Stance.evasive, Stance.evasive),
        (Stance.cooperative, Stance.hostile, Stance.cooperative),  # no such leap
        (Stance.cooperative, Stance.broken, Stance.cooperative),  # only by confrontation
        (Stance.hostile, Stance.cooperative, Stance.hostile),  # no instant recovery
        (Stance.broken, Stance.cooperative, Stance.broken),  # absorbing
    ],
)
def test_the_machine_decides_the_stance(
    current: Stance, suggested: Stance, expected: Stance
) -> None:
    """RN-023. The model suggests; an illegal move is quietly overruled."""
    assert stance_machine.settle(current, suggested) == expected


def test_an_overruled_stance_is_reported(match: Match) -> None:
    """Not an error for the player, but worth counting in the evals."""
    model = Scripted(_reply(stance=Stance.broken))

    result = ask(match, "sus-1", "e então?", catalog=load("pt-BR"), model=model)

    assert result.stance_overruled
    assert result.statement is not None
    assert result.statement.stance is Stance.cooperative


# --- the output guard -----------------------------------------------------


def test_a_canary_in_the_reply_is_rejected(match: Match) -> None:
    """RN-012. Discarded, never repaired."""
    dossier = build(match, "sus-1")
    secret = next(f for f in match.case.facts if f.canary)

    with pytest.raises(ReplyRejected) as raised:
        check(_reply(line=f"Bem, {secret.canary}, senhor."), dossier)

    assert raised.value.check == "canary"


def test_citing_a_fact_from_another_dossier_is_rejected(match: Match) -> None:
    """RN-010: means the context was assembled wrong, not that they lied."""
    dossier = build(match, "sus-1")
    known = {f.id for f in dossier.facts}
    foreign = next(f.id for f in match.case.facts if f.id not in known)

    with pytest.raises(ReplyRejected) as raised:
        check(_reply(fact_referenced=foreign), dossier)

    assert raised.value.check == "scope"


def test_citing_a_fact_they_do_hold_is_allowed(match: Match) -> None:
    dossier = build(match, "sus-1")

    check(_reply(fact_referenced=dossier.facts[0].id), dossier)


def test_an_empty_line_is_not_an_answer(match: Match) -> None:
    with pytest.raises(ReplyRejected, match="empty"):
        check(_reply(line="   "), build(match, "sus-1"))


# --- the turn ------------------------------------------------------------


def test_a_good_reply_becomes_a_statement(match: Match) -> None:
    model = Scripted(_reply(lied=True))

    result = ask(match, "sus-1", "onde você estava às 22h?", catalog=load("pt-BR"), model=model)

    assert result.statement is not None
    assert result.statement.character == "sus-1"
    assert result.statement.lied is True
    assert result.match.said_by("sus-1") == (result.statement,)
    assert result.match.stance_of("sus-1") is Stance.cooperative


def test_a_rejected_reply_still_costs_the_turn(match: Match) -> None:
    """A budget that only charged for good answers is a budget to farm."""
    model = Scripted(_reply(line="CN-deadbeef"))

    result = ask(match, "sus-1", "e então?", catalog=load("pt-BR"), model=model)

    assert result.statement is None
    assert result.rejection is not None
    assert result.match.turns_left == match.turns_left - 1
    assert result.match.statements == ()


def test_an_unavailable_model_costs_the_turn_too(match: Match) -> None:
    model = Scripted(failure=ModelUnavailable("no route to host"))

    result = ask(match, "sus-1", "e então?", catalog=load("pt-BR"), model=model)

    assert result.statement is None
    assert result.match.turns_left == match.turns_left - 1


def test_turns_run_out(match: Match) -> None:
    spent = match.model_copy(update={"turns_left": 0})

    with pytest.raises(NoTurnsLeft):
        ask(spent, "sus-1", "?", catalog=load("pt-BR"), model=Scripted(_reply()))


def test_statements_accumulate_and_reach_the_next_prompt(match: Match) -> None:
    """RN-021 needs the record; the character needs to remember what they said."""
    model = Scripted(_reply(line="Eu estava na adega."))

    first = ask(match, "sus-1", "onde?", catalog=load("pt-BR"), model=model)
    ask(first.match, "sus-1", "e depois?", catalog=load("pt-BR"), model=model)

    assert "Eu estava na adega." in model.prompts[-1]["system"]


def test_one_suspects_memory_does_not_reach_another(match: Match) -> None:
    """RN-013: no shared context bus between NPCs."""
    model = Scripted(_reply(line="Eu estava na adega."))

    first = ask(match, "sus-1", "onde?", catalog=load("pt-BR"), model=model)
    ask(first.match, "sus-2", "e você?", catalog=load("pt-BR"), model=model)

    assert "Eu estava na adega." not in model.prompts[-1]["system"]


def test_the_whole_turn_runs_on_a_fake_model(match: Match) -> None:
    """No key, no network: the guarded pipeline is exercised end to end."""
    result = ask(match, "sus-1", "onde você estava?", catalog=load("pt-BR"), model=FakeModel())

    assert result.statement is not None
    assert "[fake]" in result.statement.line
    assert result.statement.stance in set(Stance)


def test_the_dossier_is_the_only_type_the_prompt_builder_sees() -> None:
    """A signature check: `render` cannot reach a solution it is not given."""
    import inspect

    parameters = inspect.signature(render).parameters

    assert parameters["dossier"].annotation is Dossier
