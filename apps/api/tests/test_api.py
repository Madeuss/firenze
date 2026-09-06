"""HTTP tests, against the real database and a substituted model.

The interesting assertions here are about what does *not* come back. A response
that accidentally carried `lied` would hand the player a lie detector, and one
that carried a rejection detail could quote the canary token it was rejected
for.
"""

import os
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from firenze.api import connection, model_port
from firenze.config import settings
from firenze.domain import Stance
from firenze.generation import generate
from firenze.interrogation.models import NpcReply
from firenze.main import app
from firenze.model import FakeModel
from firenze.storage import metadata

URL = os.environ.get(
    "FIRENZE_TEST_DATABASE_URL",
    "postgresql+psycopg://firenze:firenze@localhost:5433/firenze",
)


def _reachable() -> bool:
    """A short timeout on purpose: without one, a missing database costs four
    minutes of retries before the suite decides to skip."""
    try:
        create_engine(URL, connect_args={"connect_timeout": 2}).connect().close()
    except OperationalError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _reachable(), reason=f"no database at {URL} — start one with `make dev`"
)


class Scripted:
    def __init__(self, reply: NpcReply | None = None, failure: Exception | None = None) -> None:
        self._reply = reply
        self._failure = failure

    @property
    def name(self) -> str:
        return "scripted"

    def complete(self, **kwargs: Any) -> Any:
        if self._failure is not None:
            raise self._failure
        return self._reply


@pytest.fixture
def client() -> Iterator[TestClient]:
    """One transaction for the whole test, shared by every request in it.

    A connection per request would roll back the match before the next call
    could see it — the requests in one test are one story, not three.
    """
    engine = create_engine(URL)
    metadata.create_all(engine)

    with engine.connect() as open_connection:
        transaction = open_connection.begin()
        app.dependency_overrides[connection] = lambda: open_connection
        app.dependency_overrides[model_port] = FakeModel
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()
        transaction.rollback()


def _start(client: TestClient, seed: int = 42) -> dict[str, Any]:
    response = client.post("/matches", json={"seed": seed, "locale": "pt-BR"})
    assert response.status_code == 201
    return dict(response.json())


def test_starting_a_match_returns_the_briefing(client: TestClient) -> None:
    state = _start(client)

    assert state["turns_left"] == 30
    assert len(state["cast"]) == 7
    assert state["known"], "the body was found; that much is public"
    assert state["notebook"] == []


def test_the_briefing_never_carries_the_solution(client: TestClient) -> None:
    """RN-011 at the last place it could leak: the wire."""
    solution = generate(seed=42).solution
    body = client.post("/matches", json={"seed": 42, "locale": "pt-BR"}).text

    assert solution.means_key not in body
    assert solution.motive_key not in body
    for fact_id in solution.chain:
        assert fact_id not in body


def test_a_suspect_answers_and_the_turn_is_charged(client: TestClient) -> None:
    match = _start(client)

    response = client.post(
        f"/matches/{match['id']}/turns",
        json={"suspect": "sus-1", "question": "onde você estava às 22h?"},
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["answered"] is True
    assert answer["line"]
    assert answer["turns_left"] == 29


def test_an_answer_never_carries_the_bookkeeping(client: TestClient) -> None:
    """`lied` is how the house keeps its books, not something the player may see."""
    match = _start(client)

    answer = client.post(
        f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "e então?"}
    ).json()

    for hidden in ("lied", "fact_referenced", "clue_revealed"):
        assert hidden not in answer


def test_a_rejected_reply_says_so_without_saying_why(client: TestClient) -> None:
    """The rejection detail can quote a canary. It goes to the log, never the wire."""
    case = generate(seed=42).case
    canary = next(f.canary for f in case.facts if f.canary)
    app.dependency_overrides[model_port] = lambda: Scripted(
        NpcReply(line=f"Ora, {canary}...", stance=Stance.cooperative, lied=False)
    )
    match = _start(client)

    response = client.post(
        f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "e então?"}
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["answered"] is False
    assert answer["reason"] == "rejected"
    assert answer["turns_left"] == 29, "a discarded reply still costs the turn"
    assert canary not in response.text


def test_the_notebook_accumulates(client: TestClient) -> None:
    match = _start(client)
    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"})

    state = client.get(f"/matches/{match['id']}").json()

    assert len(state["notebook"]) == 1
    assert state["notebook"][0]["question"] == "onde?"
    assert state["turns_left"] == 29
    assert next(c for c in state["cast"] if c["id"] == "sus-1")["stance"]


def test_questioning_somebody_who_is_not_in_the_case(client: TestClient) -> None:
    match = _start(client)

    response = client.post(
        f"/matches/{match['id']}/turns", json={"suspect": "sus-99", "question": "?"}
    )

    assert response.status_code == 422


def test_an_unknown_match_is_not_found(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"

    turn = client.post(f"/matches/{missing}/turns", json={"suspect": "sus-1", "question": "?"})

    assert client.get(f"/matches/{missing}").status_code == 404
    assert turn.status_code == 404


def test_no_provider_configured_is_a_deployment_problem(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """503, and the turn is not charged: nothing was asked of anybody.

    Exercises the real dependency by unsetting the provider, rather than
    substituting one that raises — otherwise the test proves the test.
    """
    match = _start(client)
    del app.dependency_overrides[model_port]
    monkeypatch.setattr(settings, "model_provider", "none")

    response = client.post(
        f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "?"}
    )

    assert response.status_code == 503
    assert client.get(f"/matches/{match['id']}").json()["turns_left"] == 30


def test_an_empty_question_is_refused(client: TestClient) -> None:
    match = _start(client)

    response = client.post(
        f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": ""}
    )

    assert response.status_code == 422
