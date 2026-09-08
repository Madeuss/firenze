"""Storage tests, against a real Postgres.

Not against SQLite. The schema uses JSONB and a composite unique constraint, and
a test that passes on a database the application will never run on proves that
the test passes. `make dev` starts the server these expect; `conftest.py`
creates the database and migrates it.
"""

import uuid

import pytest
from sqlalchemy import create_engine, text

from conftest import needs_database
from firenze.domain import Match, Stance, Turn
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

pytestmark = needs_database


@pytest.fixture
def connection(database_url: str):  # type: ignore[no-untyped-def]
    """A transaction rolled back at the end, so tests never see each other."""
    engine = create_engine(database_url)
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
    # Counted by identity rather than by table: a shared database carries rows
    # from anything else that ran, and a test that assumes an empty table is a
    # test that fails for reasons unrelated to what it checks.
    rows = connection.execute(
        text(
            "SELECT count(*) FROM cases "
            "WHERE seed = :seed AND generator_version = :version AND setting = :setting"
        ),
        {
            "seed": full.case.seed,
            "version": full.case.generator_version,
            "setting": full.case.setting,
        },
    ).scalar_one()
    assert rows == 1


def test_loading_a_case_cannot_reach_the_solution(connection) -> None:  # type: ignore[no-untyped-def]
    """RN-011 in the layer where it is easiest to lose.

    The solution lives in another table, so this read does not touch it — the
    guarantee is the query, not the caller's restraint.
    """
    full = generate(seed=42)
    case_id = save_case(connection, full)

    loaded = load_case(connection, case_id)

    # `Case` has no Solution on it: no culprit field, no means, no chain. The
    # motive *does* appear, inside the scoped fact that makes it discoverable
    # (RN-034) — isolation is a property of scopes and dossiers, never of the
    # blob, and it always was: the clue fact has named the culprit since #11.
    assert not hasattr(loaded, "solution")
    assert full.solution.means_key not in loaded.model_dump_json()


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
    record_turn(connection, match_id, result.match, result.turn)

    reloaded = load_match(connection, match_id)
    assert reloaded.turns_left == 29
    assert len(reloaded.statements) == 1
    assert reloaded.statements[0].character == "sus-1"
    assert reloaded.stance_of("sus-1") is result.match.stance_of("sus-1")


def test_a_rejected_turn_is_recorded_with_no_line(connection) -> None:  # type: ignore[no-untyped-def]
    """The turn is spent, and the record says where it went. (RN-030)

    Persisting only the answers would leave a finished match showing thirty
    turns spent and twenty statements, with nothing to explain the other ten.
    """
    match_id = start_match(connection, generate(seed=42), "pt-BR")
    match = load_match(connection, match_id)
    rejected = Turn(
        turn=1,
        character="sus-1",
        question="e então?",
        stance=Stance.cooperative,
        rejected_by="canary",
    )

    record_turn(connection, match_id, match.model_copy(update={"turns_left": 29}), rejected)

    reloaded = load_match(connection, match_id)
    assert reloaded.turns_left == 29
    assert reloaded.statements == (), "nothing was said"
    assert len(reloaded.turns) == 1
    assert reloaded.turns[0].rejected_by == "canary"
    assert reloaded.turns[0].line == ""


def test_statements_come_back_in_the_order_they_were_said(connection) -> None:  # type: ignore[no-untyped-def]
    match_id = start_match(connection, generate(seed=42), "pt-BR")
    match = load_match(connection, match_id)

    for question in ("primeira?", "segunda?", "terceira?"):
        result = ask(match, "sus-1", question, catalog=load("pt-BR"), model=FakeModel())
        record_turn(connection, match_id, result.match, result.turn)
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
    record_turn(connection, first_id, result.match, result.turn)

    assert len(load_match(connection, first_id).statements) == 1
    assert load_match(connection, second_id).statements == ()


def test_the_turn_number_is_unique_within_a_match(connection) -> None:  # type: ignore[no-untyped-def]
    """The database refuses two turn 1s, so a retry cannot double-record."""
    from sqlalchemy.exc import IntegrityError

    match_id = start_match(connection, generate(seed=42), "pt-BR")
    match = load_match(connection, match_id)
    statement = Turn(
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


def test_the_migrations_produce_the_schema_the_code_expects(database_url: str) -> None:
    """The guard the suite was missing. (#43)

    Every other test here runs against whatever the migrations built, so a
    migration that forgot a column would fail them loudly — but only for the
    columns some test happens to touch. This compares the whole thing: what
    `alembic upgrade head` produced against what `tables.py` declares.

    It is the check that `create_all` used to hide, by quietly making up the
    difference at test time.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    engine = create_engine(database_url)
    with engine.connect() as open_connection:
        context = MigrationContext.configure(open_connection)
        difference = compare_metadata(context, metadata)

    assert difference == [], f"the migrations and the model disagree: {difference}"
