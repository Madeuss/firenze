"""Storage tests, against a real Postgres.

Not against SQLite. The schema uses JSONB and a composite unique constraint, and
a test that passes on a database the application will never run on proves that
the test passes. `make dev` starts the one these expect.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from firenze.domain import Match, Stance, Statement
from firenze.generation import generate
from firenze.i18n import load
from firenze.interrogation import ask
from firenze.model import FakeModel
from firenze.storage import (
    NotFound,
    load_case,
    load_full_case,
    load_match,
    metadata,
    record_turn,
    save_case,
    start_match,
)

URL = os.environ.get(
    "FIRENZE_TEST_DATABASE_URL",
    "postgresql+psycopg://firenze:firenze@localhost:5433/firenze",
)


def _reachable() -> bool:
    try:
        create_engine(URL).connect().close()
    except OperationalError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _reachable(),
    reason=f"no database at {URL} — start one with `make dev`",
)


@pytest.fixture
def connection():  # type: ignore[no-untyped-def]
    """A transaction rolled back at the end, so tests never see each other."""
    engine = create_engine(URL)
    metadata.create_all(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


def test_a_case_survives_a_round_trip(connection) -> None:  # type: ignore[no-untyped-def]
    full = generate(seed=42)

    case_id = save_case(connection, full)

    assert load_full_case(connection, case_id) == full


def test_saving_the_same_case_twice_gives_the_same_row(connection) -> None:  # type: ignore[no-untyped-def]
    """Identity is seed, generator version and setting — not a fresh uuid."""
    full = generate(seed=42)

    first = save_case(connection, full)
    second = save_case(connection, full)

    assert first == second
    assert connection.execute(text("SELECT count(*) FROM cases")).scalar_one() == 1


def test_loading_a_case_cannot_reach_the_solution(connection) -> None:  # type: ignore[no-untyped-def]
    """RN-011 in the layer where it is easiest to lose.

    The solution lives in another table, so this read does not touch it — the
    guarantee is the query, not the caller's restraint.
    """
    full = generate(seed=42)
    case_id = save_case(connection, full)

    serialised = load_case(connection, case_id).model_dump_json()

    assert full.solution.culprit not in serialised.replace('"sus-', "")
    assert full.solution.means_key not in serialised
    assert full.solution.motive_key not in serialised


def test_a_missing_case_is_not_found(connection) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(NotFound):
        load_case(connection, uuid.uuid4())


def test_a_match_survives_a_round_trip(connection) -> None:  # type: ignore[no-untyped-def]
    match_id = start_match(connection, generate(seed=42), "pt-BR")

    match = load_match(connection, match_id)

    assert match.locale == "pt-BR"
    assert match.turns_left == 30
    assert match.statements == ()
    assert match.full_case == generate(seed=42)


def test_a_turn_persists_the_statement_the_stance_and_the_budget(connection) -> None:  # type: ignore[no-untyped-def]
    match_id = start_match(connection, generate(seed=42), "pt-BR")
    match = load_match(connection, match_id)

    result = ask(match, "sus-1", "onde você estava?", catalog=load("pt-BR"), model=FakeModel())
    record_turn(connection, match_id, result.match, result.statement)

    reloaded = load_match(connection, match_id)
    assert reloaded.turns_left == 29
    assert len(reloaded.statements) == 1
    assert reloaded.statements[0].character == "sus-1"
    assert reloaded.stance_of("sus-1") is result.match.stance_of("sus-1")


def test_a_rejected_turn_still_moves_the_budget(connection) -> None:  # type: ignore[no-untyped-def]
    """No statement to record, and the turn is spent anyway. (RN-030)"""
    match_id = start_match(connection, generate(seed=42), "pt-BR")
    match = load_match(connection, match_id)
    spent = match.model_copy(update={"turns_left": 29})

    record_turn(connection, match_id, spent, None)

    reloaded = load_match(connection, match_id)
    assert reloaded.turns_left == 29
    assert reloaded.statements == ()


def test_statements_come_back_in_the_order_they_were_said(connection) -> None:  # type: ignore[no-untyped-def]
    match_id = start_match(connection, generate(seed=42), "pt-BR")
    match = load_match(connection, match_id)

    for question in ("primeira?", "segunda?", "terceira?"):
        result = ask(match, "sus-1", question, catalog=load("pt-BR"), model=FakeModel())
        record_turn(connection, match_id, result.match, result.statement)
        match = result.match

    said = load_match(connection, match_id).statements

    assert [s.turn for s in said] == [1, 2, 3]
    assert [s.question for s in said] == ["primeira?", "segunda?", "terceira?"]


def test_two_matches_on_the_same_case_do_not_share_statements(connection) -> None:  # type: ignore[no-untyped-def]
    """One case, two playthroughs, no leakage between them."""
    full = generate(seed=42)
    first_id = start_match(connection, full, "pt-BR")
    second_id = start_match(connection, full, "en")

    match = load_match(connection, first_id)
    result = ask(match, "sus-1", "onde?", catalog=load("pt-BR"), model=FakeModel())
    record_turn(connection, first_id, result.match, result.statement)

    assert len(load_match(connection, first_id).statements) == 1
    assert load_match(connection, second_id).statements == ()


def test_the_turn_number_is_unique_within_a_match(connection) -> None:  # type: ignore[no-untyped-def]
    """The database refuses two turn 1s, so a retry cannot double-record."""
    from sqlalchemy.exc import IntegrityError

    match_id = start_match(connection, generate(seed=42), "pt-BR")
    match = load_match(connection, match_id)
    statement = Statement(
        turn=1,
        character="sus-1",
        question="?",
        line="...",
        stance=Stance.cooperative,
        lied=False,
    )

    record_turn(connection, match_id, match, statement)

    with pytest.raises(IntegrityError):
        record_turn(connection, match_id, match, statement)


def test_a_match_in_memory_and_a_match_from_the_database_behave_the_same(connection) -> None:  # type: ignore[no-untyped-def]
    """The store is a detail; the domain object is the same either way."""
    full = generate(seed=42)
    match_id = start_match(connection, full, "pt-BR")

    assert load_match(connection, match_id) == Match(full_case=full, locale="pt-BR")
