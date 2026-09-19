"""Who may start a match, and who may touch one. (T-11, T-12)

The threat model calls both of these blockers for publishing, so these tests
are the evidence that the block was lifted honestly. They run the guarded
configuration — the suite everywhere else runs the open one, which is what
local development is.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from firenze.api.access import KEY_HEADER, TOKEN_HEADER, Unprotected, bucket, check_configuration
from firenze.config import settings
from firenze.main import app
from firenze.storage import engine

KEY = "a-chave-de-quem-convidou"


@pytest.fixture
def guarded(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "database_url", database_url)
    monkeypatch.setattr(settings, "access_key", SecretStr(KEY))
    engine.cache_clear()
    with TestClient(app) as client:
        yield client
    engine.cache_clear()


@pytest.fixture
def open_client(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """No key configured: the shape local development and the rest of the suite run."""
    monkeypatch.setattr(settings, "database_url", database_url)
    monkeypatch.setattr(settings, "access_key", SecretStr(""))
    engine.cache_clear()
    with TestClient(app) as client:
        yield client
    engine.cache_clear()


def _start(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/matches", json={"seed": 42, "locale": "pt-BR"}, headers={KEY_HEADER: KEY}
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_starting_a_match_needs_the_key(guarded: TestClient) -> None:
    """The route that makes spend out of nothing is the one worth a password."""
    response = guarded.post("/matches", json={"seed": 42, "locale": "pt-BR"})

    assert response.status_code == 401
    assert KEY_HEADER in response.text


def test_a_wrong_key_is_no_better_than_none(guarded: TestClient) -> None:
    response = guarded.post(
        "/matches", json={"seed": 42, "locale": "pt-BR"}, headers={KEY_HEADER: "quase"}
    )

    assert response.status_code == 401


def test_the_token_comes_back_once_and_only_at_the_start(guarded: TestClient) -> None:
    match = _start(guarded)
    token = match["owner_token"]

    assert token
    again = guarded.get(f"/matches/{match['id']}", headers={TOKEN_HEADER: token})

    assert again.status_code == 200
    assert again.json()["owner_token"] is None, "a second copy is a second way to lose it"


def test_the_notebook_is_closed_to_whoever_lacks_the_token(guarded: TestClient) -> None:
    """Holding the id was the whole of the old security."""
    match = _start(guarded)

    assert guarded.get(f"/matches/{match['id']}").status_code == 403
    alheio = guarded.get(f"/matches/{match['id']}", headers={TOKEN_HEADER: "outro"})
    assert alheio.status_code == 403


def test_the_turns_of_a_match_cannot_be_spent_by_a_stranger(guarded: TestClient) -> None:
    """The one that costs money, and the reason this shipped before the URL."""
    match = _start(guarded)

    response = guarded.post(
        f"/matches/{match['id']}/turns", json={"suspect": "sus-1", "question": "onde?"}
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", ""),
        ("get", "/review"),
        ("post", "/turns"),
        ("post", "/confrontations"),
        ("post", "/accusation"),
        ("post", "/accusation/draft"),
    ],
)
def test_every_route_that_takes_a_match_id_checks_the_owner(
    guarded: TestClient, method: str, path: str
) -> None:
    """Written as a sweep because the failure mode is a route added later.

    A new endpoint under /matches/{match_id} that forgets the dependency is a
    notebook handed to a stranger, and nothing else in the suite would notice.
    """
    match = _start(guarded)

    url = f"/matches/{match['id']}{path}"
    response = guarded.get(url) if method == "get" else guarded.post(url, json={})

    assert response.status_code == 403, f"{method.upper()} {path} let a stranger through"


def test_the_owner_gets_in(guarded: TestClient) -> None:
    match = _start(guarded)
    headers = {TOKEN_HEADER: match["owner_token"]}

    assert guarded.get(f"/matches/{match['id']}", headers=headers).status_code == 200


def test_a_match_that_does_not_exist_says_so_rather_than_forbidden(guarded: TestClient) -> None:
    """404 before 403: there is no owner to be wrong about."""
    missing = "00000000-0000-0000-0000-000000000000"

    assert guarded.get(f"/matches/{missing}").status_code == 404


def test_the_window_closes_after_enough_requests(guarded: TestClient) -> None:
    """T-12. The access key stops strangers; this bounds an invited player."""
    bucket().forget()
    limit = settings.rate_limit_per_minute

    codes = [
        guarded.post(
            "/matches", json={"seed": 42, "locale": "pt-BR"}, headers={KEY_HEADER: KEY}
        ).status_code
        for _ in range(limit + 1)
    ]

    assert codes[-1] == 429
    assert codes.count(429) == 1, "the window closed early or not at all"


def test_a_prod_process_refuses_to_start_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The open default is a footgun in exactly one direction. This is the other end."""
    monkeypatch.setattr(settings, "environment", "prod")
    monkeypatch.setattr(settings, "access_key", SecretStr(""))

    with pytest.raises(Unprotected, match="FIRENZE_ACCESS_KEY"):
        check_configuration()


def test_an_open_deployment_stays_open(open_client: TestClient) -> None:
    """Local development and this suite: no key, no ceremony, nothing to check."""
    match = open_client.post("/matches", json={"seed": 42, "locale": "pt-BR"})

    assert match.status_code == 201
    assert open_client.get(f"/matches/{match.json()['id']}").status_code == 200
