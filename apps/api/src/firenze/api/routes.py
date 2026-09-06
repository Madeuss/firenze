"""The three endpoints a single-NPC interrogation needs.

    POST /matches              start one
    GET  /matches/{id}         the notebook
    POST /matches/{id}/turns   ask a question

Every response is built from `MatchState` and friends rather than from the
domain objects, so the solution and the per-turn bookkeeping cannot reach a
client by being forgotten about.

Nothing streams yet. The front end is phase 5, and a streaming shape chosen
before there is anything to render is a shape chosen blind (ADR-0007 says the
port will need a second method for it).
"""

import logging
import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from firenze.api.schemas import (
    Answer,
    CastMember,
    KnownFact,
    MatchState,
    NewMatch,
    Question,
    Said,
)
from firenze.config import settings
from firenze.domain import Match, Role
from firenze.generation import UnsolvableCase, generate
from firenze.i18n import UnknownLocale, load
from firenze.interrogation import ask
from firenze.interrogation.turn import NoTurnsLeft
from firenze.model import ModelUnavailable, StructuredModel, resolve
from firenze.storage import NotFound, load_match, record_turn, start_match, transaction

log = logging.getLogger(__name__)
router = APIRouter(prefix="/matches", tags=["match"])


def connection() -> Iterator[Connection]:
    with transaction() as open_connection:
        yield open_connection


def model_port() -> StructuredModel:
    """The configured model, as a dependency so a test can supply its own.

    No provider configured is a deployment problem, not a spent turn, so it
    fails before the handler charges anything.
    """
    try:
        return resolve(
            settings.model_provider,
            model=settings.model_name,
            base_url=settings.model_base_url,
            api_key=settings.model_api_key.get_secret_value(),
        )
    except ModelUnavailable as unavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(unavailable)) from unavailable


# Annotated dependencies rather than defaults: the modern FastAPI form, and the
# one that does not need a lint suppression to say what it means.
Db = Annotated[Connection, Depends(connection)]
Model = Annotated[StructuredModel, Depends(model_port)]


def _state(match_id: uuid.UUID, match: Match) -> MatchState:
    case = match.case
    catalog = load(match.locale)

    return MatchState(
        id=match_id,
        seed=case.seed,
        locale=match.locale,
        turns_left=match.turns_left,
        cast=tuple(
            CastMember(
                id=person.id,
                name=person.name,
                role=person.role.value,
                stance=match.stances.get(person.id) if person.role is Role.suspect else None,
            )
            for person in case.cast
        ),
        known=tuple(
            KnownFact(id=fact.id, text=catalog.fact(case, fact))
            for fact in case.facts
            if fact.scope.public
        ),
        notebook=tuple(
            Said(
                turn=said.turn,
                character=said.character,
                question=said.question,
                line=said.line,
                stance=said.stance,
            )
            for said in match.statements
        ),
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Start a match")
def create(body: NewMatch, db: Db) -> MatchState:
    try:
        full = generate(seed=body.seed, suspects=body.suspects)
        load(body.locale)
    except UnknownLocale as unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(unknown)) from unknown
    except (UnsolvableCase, ValueError) as failure:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(failure)) from failure

    match_id = start_match(db, full, body.locale)
    return _state(match_id, load_match(db, match_id))


@router.get("/{match_id}", summary="The notebook")
def read(match_id: uuid.UUID, db: Db) -> MatchState:
    try:
        return _state(match_id, load_match(db, match_id))
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing


@router.post("/{match_id}/turns", summary="Question a suspect")
def take_turn(match_id: uuid.UUID, body: Question, db: Db, model: Model) -> Answer:
    try:
        match = load_match(db, match_id)
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing

    if body.suspect not in {s.id for s in match.case.suspects}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"{body.suspect} is not a suspect in this case"
        )

    try:
        result = ask(match, body.suspect, body.question, catalog=load(match.locale), model=model)
    except NoTurnsLeft as spent:
        raise HTTPException(status.HTTP_409_CONFLICT, str(spent)) from spent

    record_turn(db, match_id, result.match, result.statement)

    if result.statement is None:
        # The detail can quote a canary token. It goes to the log, never the wire.
        log.warning("turn rejected on match %s: %s", match_id, result.rejection)
        return Answer(
            answered=False,
            character=body.suspect,
            reason="model_unavailable" if "model" in (result.rejection or "") else "rejected",
            turns_left=result.match.turns_left,
        )

    return Answer(
        answered=True,
        character=body.suspect,
        line=result.statement.line,
        stance=result.statement.stance,
        turns_left=result.match.turns_left,
    )
