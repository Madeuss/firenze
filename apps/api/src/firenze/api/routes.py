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
    Confrontation,
    KnownFact,
    MatchState,
    NewAccusation,
    NewMatch,
    Outcome,
    Question,
    Said,
)
from firenze.config import settings
from firenze.domain import Match, Role
from firenze.generation import UnsolvableCase, generate
from firenze.i18n import UnknownLocale, load
from firenze.interrogation import ask, confront
from firenze.interrogation.turn import MatchIsOver, NoTurnsLeft, UnknownEvidence
from firenze.model import ModelUnavailable, StructuredModel, resolve
from firenze.narration import write as narrate
from firenze.storage import NotFound, load_match, record_turn, start_match, transaction
from firenze.verdict import Accusation, AlreadyAccused, NotASuspect, judge

log = logging.getLogger(__name__)
router = APIRouter(prefix="/matches", tags=["match"])


def connection() -> Iterator[Connection]:
    with transaction() as open_connection:
        yield open_connection


def _resolve(name: str) -> StructuredModel:
    try:
        return resolve(
            settings.model_provider,
            model=name,
            base_url=settings.model_base_url,
            api_key=settings.model_api_key.get_secret_value(),
        )
    except ModelUnavailable as unavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(unavailable)) from unavailable


def model_port() -> StructuredModel:
    """The model a suspect answers with.

    No provider configured is a deployment problem, not a spent turn, so it
    fails before the handler charges anything.
    """
    return _resolve(settings.model_name)


def classifier_port() -> StructuredModel:
    """The model that labels player input. The cheapest one that can (RN-040)."""
    return _resolve(settings.classifier_model_name or settings.model_name)


# Annotated dependencies rather than defaults: the modern FastAPI form, and the
# one that does not need a lint suppression to say what it means.
Db = Annotated[Connection, Depends(connection)]
Model = Annotated[StructuredModel, Depends(model_port)]
Classifier = Annotated[StructuredModel, Depends(classifier_port)]


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
        evidence=tuple(sorted(match.evidence)),
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


@router.post("/{match_id}/accusation", summary="Name a culprit and end the match")
def accuse(match_id: uuid.UUID, body: NewAccusation, db: Db) -> Outcome:
    """No model is involved. The outcome is arithmetic (RN-032)."""
    try:
        match = load_match(db, match_id)
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing

    try:
        verdict = judge(match, Accusation(culprit=body.culprit, evidence=body.evidence))
    except AlreadyAccused as decided:
        raise HTTPException(status.HTTP_409_CONFLICT, str(decided)) from decided
    except NotASuspect as unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(unknown)) from unknown

    decided_match = match.model_copy(
        update={"accused_culprit": body.culprit, "accused_evidence": tuple(body.evidence)}
    )
    record_turn(db, match_id, decided_match, None)

    catalog = load(match.locale)
    # The ending is written after the outcome is decided, and its absence
    # changes nothing above this line (RN-032).
    epilogue: str | None = None
    try:
        epilogue = narrate(
            verdict,
            body.culprit,
            match.case,
            catalog,
            model=_resolve(settings.model_name),
        )
    except HTTPException:
        log.info("no model configured; the match ends without an epilogue")

    return Outcome(
        correct=verdict.correct,
        accused=body.culprit,
        culprit=verdict.culprit,
        means=catalog.means(verdict.means_key),
        motive=catalog.motive(verdict.motive_key),
        score=verdict.score,
        culprit_points=verdict.culprit_points,
        evidence_points=verdict.evidence_points,
        speed_points=verdict.speed_points,
        evidence_expected=verdict.evidence_expected,
        evidence_hit=verdict.evidence_hit,
        turns_left=match.turns_left,
        epilogue=epilogue,
    )


@router.post("/{match_id}/confrontations", summary="Show a suspect a piece of evidence")
def take_confrontation(match_id: uuid.UUID, body: Confrontation, db: Db, model: Model) -> Answer:
    """Costs two turns, and only the evidence the player already holds."""
    try:
        match = load_match(db, match_id)
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing

    if body.suspect not in {s.id for s in match.case.suspects}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"{body.suspect} is not a suspect in this case",
        )

    try:
        result = confront(
            match, body.suspect, body.evidence, catalog=load(match.locale), model=model
        )
    except UnknownEvidence as unheld:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(unheld)) from unheld
    except (NoTurnsLeft, MatchIsOver) as over:
        raise HTTPException(status.HTTP_409_CONFLICT, str(over)) from over
    except ModelUnavailable as unreachable:
        log.warning("confrontation abandoned on match %s: %s", match_id, unreachable)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "the model is unreachable"
        ) from unreachable

    record_turn(db, match_id, result.match, result.statement)

    if result.statement is None:
        log.warning("confrontation rejected on match %s: %s", match_id, result.rejection)
        return Answer(
            answered=False,
            character=body.suspect,
            reason="rejected",
            turns_left=result.match.turns_left,
        )

    return Answer(
        answered=True,
        character=body.suspect,
        line=result.statement.line,
        stance=result.statement.stance,
        alibi_broken=result.alibi_broken,
        turns_left=result.match.turns_left,
    )


@router.post("/{match_id}/turns", summary="Question a suspect")
def take_turn(
    match_id: uuid.UUID, body: Question, db: Db, model: Model, classifier: Classifier
) -> Answer:
    try:
        match = load_match(db, match_id)
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing

    if body.suspect not in {s.id for s in match.case.suspects}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"{body.suspect} is not a suspect in this case"
        )

    try:
        result = ask(
            match,
            body.suspect,
            body.question,
            catalog=load(match.locale),
            model=model,
            classifier=classifier,
        )
    except (NoTurnsLeft, MatchIsOver) as over:
        raise HTTPException(status.HTTP_409_CONFLICT, str(over)) from over
    except ModelUnavailable as unreachable:
        # Nothing was asked of anybody, so nothing happened and nothing is charged.
        log.warning("turn abandoned on match %s: %s", match_id, unreachable)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "the model is unreachable"
        ) from unreachable

    record_turn(db, match_id, result.match, result.statement)

    if result.statement is None:
        # The detail can quote a canary token. It goes to the log, never the wire.
        log.warning("turn rejected on match %s: %s", match_id, result.rejection)
        return Answer(
            answered=False,
            character=body.suspect,
            reason="rejected",
            turns_left=result.match.turns_left,
        )

    return Answer(
        answered=True,
        character=body.suspect,
        line=result.statement.line,
        stance=result.statement.stance,
        turns_left=result.match.turns_left,
    )
