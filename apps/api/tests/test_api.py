"""HTTP tests, against the real database and a substituted model.

The interesting assertions here are about what does *not* come back. A response
that accidentally carried `lied` would hand the player a lie detector, and one
that carried a rejection detail could quote the canary token it was rejected
for.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from conftest import needs_database
from firenze.api import classifier_port, connection, model_port
from firenze.config import settings
from firenze.domain import Intent, Stance
from firenze.generation import generate
from firenze.interrogation.models import NpcReply
from firenze.main import app
from firenze.model import FakeModel
from firenze.safety import Classification

pytestmark = needs_database


class Scripted:
    """Plays both parts: the classifier first, then the suspect (RN-040)."""

    def __init__(self, reply: NpcReply | None = None, failure: Exception | None = None) -> None:
        self._reply = reply
        self._failure = failure

    @property
    def name(self) -> str:
        return "scripted"

    def complete(self, **kwargs: Any) -> Any:
        if kwargs["schema"] is Classification:
            return Classification(intent=Intent.question, reason="a question")
        if self._failure is not None:
            raise self._failure
        return self._reply


@pytest.fixture
def client(database_url: str) -> Iterator[TestClient]:
    """A connection per request, committed for real, like in production.

    It used to be one shared transaction rolled back at the end of the test —
    cheaper, and it hid the bug it was hiding: with every request on the same
    open transaction, a handler that never committed still looked fine to the
    next call. In a browser it was not fine, because the front end asks for the
    match on its own connection the moment a turn returns.

    So the requests here commit, against a database that is dropped when the
    run ends. A write that is not committed now fails the next read, in the
    same test, for the same reason it would fail in front of a player.
    """
    engine = create_engine(database_url)

    def por_requisicao() -> Iterator[Connection]:
        with engine.connect() as open_connection:
            yield open_connection

    app.dependency_overrides[connection] = por_requisicao
    app.dependency_overrides[model_port] = FakeModel
    app.dependency_overrides[classifier_port] = FakeModel
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


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
    del app.dependency_overrides[classifier_port]
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


# --- the review -----------------------------------------------------------


def _accuse(client: TestClient, match_id: str, culprit: str = "sus-1") -> dict[str, Any]:
    response = client.post(f"/matches/{match_id}/accusation", json={"culprit": culprit})
    assert response.status_code == 200
    return dict(response.json())


def test_a_match_still_being_played_has_no_review(client: TestClient) -> None:
    """The same payload mid-match would be a lie detector, so it is a 409."""
    match = _start(client)

    response = client.get(f"/matches/{match['id']}/review")

    assert response.status_code == 409


def test_the_review_of_an_unknown_match_is_not_found(client: TestClient) -> None:
    assert client.get("/matches/00000000-0000-0000-0000-000000000000/review").status_code == 404


def test_the_review_lists_the_rejected_turns_too(client: TestClient) -> None:
    """The point of the whole record: a turn that produced nothing is in it."""
    case = generate(seed=42).case
    canary = next(f.canary for f in case.facts if f.canary)
    match = _start(client)

    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"})
    app.dependency_overrides[model_port] = lambda: Scripted(
        NpcReply(line=f"Ora, {canary}...", stance=Stance.cooperative, lied=False)
    )
    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-2", "question": "e você?"})
    app.dependency_overrides[model_port] = FakeModel
    _accuse(client, match["id"])

    response = client.get(f"/matches/{match['id']}/review")
    review = response.json()

    assert [t["turn"] for t in review["record"]] == [1, 2]
    assert review["record"][0]["answered"] is True
    assert review["record"][1]["answered"] is False
    assert review["record"][1]["rejected_by"] == "canary"
    assert review["record"][1]["line"] is None
    assert canary not in response.text, "the name of the check travels, never the text"


def test_the_review_reconciles_the_budget(client: TestClient) -> None:
    """Costs recorded plus turns left equals the budget. No turn goes missing."""
    match = _start(client)
    for who in ("sus-1", "sus-2", "sus-3"):
        client.post(f"/matches/{match['id']}/turns", json={"suspect": who, "question": "onde?"})
    _accuse(client, match["id"])

    review = client.get(f"/matches/{match['id']}/review").json()

    assert sum(t["cost"] for t in review["record"]) == review["turns_spent"]
    assert review["turns_spent"] + review["turns_left"] == review["budget"] == 30


def test_the_review_shows_the_ending_the_player_was_shown(client: TestClient) -> None:
    """Recomputed, not stored — so it has to come out the same (RN-032)."""
    match = _start(client)
    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"})
    outcome = _accuse(client, match["id"])

    reviewed = client.get(f"/matches/{match['id']}/review").json()["outcome"]

    assert reviewed == {**outcome, "epilogue": None}


def test_the_review_says_when_a_clue_reached_the_player(client: TestClient) -> None:
    case = generate(seed=42).case
    secret = next(f for f in case.facts if not f.scope.public)
    app.dependency_overrides[model_port] = lambda: Scripted(
        NpcReply(line="Vi, sim.", stance=Stance.cooperative, lied=False, clue_revealed=secret.id)
    )
    match = _start(client)
    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "viu?"})
    app.dependency_overrides[model_port] = FakeModel
    _accuse(client, match["id"])

    trail = client.get(f"/matches/{match['id']}/review").json()["evidence_trail"]

    briefing = [e for e in trail if e["turn"] is None]
    given = [e for e in trail if e["turn"] is not None]
    assert briefing, "what the player started with"
    assert given[0]["id"] == secret.id
    assert given[0]["turn"] == 1
    assert given[0]["given_by"] == "sus-1"


def test_the_review_traces_how_a_stance_moved(client: TestClient) -> None:
    app.dependency_overrides[model_port] = lambda: Scripted(
        NpcReply(line="Não vou responder.", stance=Stance.evasive, lied=False)
    )
    match = _start(client)
    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"})
    app.dependency_overrides[model_port] = FakeModel
    _accuse(client, match["id"])

    trail = client.get(f"/matches/{match['id']}/review").json()["stance_trail"]

    assert trail[0]["turn"] == 1
    assert trail[0]["character"] == "sus-1"
    assert trail[0]["was"] == "cooperative"
    assert trail[0]["became"] == "evasive"


def test_the_review_remembers_the_motive_the_player_named(client: TestClient) -> None:
    """The one thing the record could not derive, so it had to be kept.

    The verdict is recomputed rather than stored (RN-032). Without the accused
    motive on the match, a review would score a correct motive as unclaimed and
    report twenty points fewer than the player was told.
    """
    solution = generate(seed=42).solution
    match = _start(client)

    outcome = client.post(
        f"/matches/{match['id']}/accusation",
        json={"culprit": solution.culprit, "motive_key": solution.motive_key},
    ).json()
    assert outcome["motive_points"] == 20

    reviewed = client.get(f"/matches/{match['id']}/review").json()["outcome"]

    assert reviewed["motive_points"] == 20
    assert reviewed["score"] == outcome["score"]


# --- the floor plan -------------------------------------------------------


def test_the_plan_is_the_house_and_the_night(client: TestClient) -> None:
    case = generate(seed=42).case
    plan = _start(client)["plan"]

    assert [r["id"] for r in plan["rooms"]] == list(case.rooms)
    assert [h["interval"] for h in plan["hours"]] == list(range(case.interval_count))
    assert plan["hours"][0]["label"] == "21h00"


def test_the_plan_is_empty_of_people(client: TestClient) -> None:
    """A filled plan would be the server solving the game.

    Reconstructing the night from what people claimed is the deduction. The
    plan is the board; the claims stay in the answers the player has to read.
    """
    case = generate(seed=42).case
    plan = _start(client)["plan"]

    rendered = repr(plan)
    for suspect in case.suspects:
        assert suspect.id not in rendered
        assert suspect.name not in rendered
    assert "claimed" not in rendered


def test_the_plan_speaks_the_match_language(client: TestClient) -> None:
    pt = client.post("/matches", json={"seed": 42, "locale": "pt-BR"}).json()["plan"]
    en = client.post("/matches", json={"seed": 42, "locale": "en"}).json()["plan"]

    assert [r["id"] for r in pt["rooms"]] == [r["id"] for r in en["rooms"]], "ids are stable"
    assert [r["name"] for r in pt["rooms"]] != [r["name"] for r in en["rooms"]]


def test_the_review_says_what_each_answer_claimed(client: TestClient) -> None:
    """How the plan fills itself in once the match is over. (RN-035)"""
    app.dependency_overrides[model_port] = lambda: Scripted(
        NpcReply(
            line="Estava no escritório.",
            stance=Stance.cooperative,
            lied=False,
            claimed_room="study",
            claimed_interval=2,
        )
    )
    match = _start(client)
    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"})
    app.dependency_overrides[model_port] = FakeModel
    _accuse(client, match["id"])

    recorded = client.get(f"/matches/{match['id']}/review").json()["record"][0]

    assert recorded["claimed_room"] == "study"
    assert recorded["claimed_interval"] == 2


def test_an_answer_mid_match_still_hides_what_it_claimed(client: TestClient) -> None:
    """The review may show it. A turn may not, or the plan fills itself."""
    match = _start(client)

    answer = client.post(
        f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"}
    ).json()

    assert "claimed_room" not in answer
    assert "claimed_interval" not in answer


# --- the notebook is the only record the front needs ----------------------


def test_the_notebook_carries_the_turns_that_produced_nothing(client: TestClient) -> None:
    """A front that had to remember rejections would be a second source.

    The first version of the web client kept its own copy of each answer next
    to the notebook, and every answered turn rendered twice. The fix is not to
    dedupe on the client: it is for the notebook to be the whole record, the
    way `Match.turns` already is (RN-030).
    """
    case = generate(seed=42).case
    canary = next(f.canary for f in case.facts if f.canary)
    match = _start(client)

    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"})
    app.dependency_overrides[model_port] = lambda: Scripted(
        NpcReply(line=f"Ora, {canary}...", stance=Stance.cooperative, lied=False)
    )
    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "e então?"})

    notebook = client.get(f"/matches/{match['id']}").json()["notebook"]

    assert [entry["turn"] for entry in notebook] == [1, 2]
    assert notebook[0]["answered"] is True
    assert notebook[1]["answered"] is False
    assert notebook[1]["line"] is None
    assert notebook[1]["question"] == "e então?", "the question is the player's own"


def test_the_notebook_never_says_why_a_turn_was_discarded(client: TestClient) -> None:
    """`contradiction` would tell the player something they did not earn."""
    case = generate(seed=42).case
    canary = next(f.canary for f in case.facts if f.canary)
    app.dependency_overrides[model_port] = lambda: Scripted(
        NpcReply(line=f"Ora, {canary}...", stance=Stance.cooperative, lied=False)
    )
    match = _start(client)

    client.post(f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"})
    response = client.get(f"/matches/{match['id']}")

    assert "rejected_by" not in response.text
    assert "canary" not in response.text


def test_the_plan_marks_where_the_body_was_found(client: TestClient) -> None:
    """Not a leak: the briefing says it in prose, in the same words.

    Prose a player has to parse by eye is not a security boundary. What the
    plan must not carry is who was where, and that is a different test.
    """
    full = generate(seed=42)
    state = _start(client)
    plan = state["plan"]

    assert plan["crime_room"] == full.case.crime_room
    assert plan["crime_interval"] == full.case.crime_interval
    # e o briefing ja dizia os dois
    briefing = state["known"][0]["text"]
    nome = next(r["name"] for r in plan["rooms"] if r["id"] == plan["crime_room"])
    hora = next(h["label"] for h in plan["hours"] if h["interval"] == plan["crime_interval"])
    assert nome in briefing
    assert hora in briefing
