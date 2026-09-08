"""The three endpoints a single-NPC interrogation needs.

    POST /matches               start one
    GET  /matches/{id}          the notebook
    POST /matches/{id}/turns    ask a question
    GET  /matches/{id}/review   the whole record, once it is over

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

from firenze.accusation import known_motives, parse, summarise
from firenze.api.schemas import (
    AccusationText,
    Answer,
    CastMember,
    Confrontation,
    DraftAccusation,
    FloorPlan,
    HeldEvidence,
    Hour,
    KnownFact,
    MatchState,
    NewAccusation,
    NewMatch,
    Outcome,
    Question,
    Review,
    ReviewedTurn,
    Room,
    Said,
    StanceMove,
)
from firenze.config import settings
from firenze.domain import Case, Match, Role, Stance
from firenze.generation import UnsolvableCase, generate
from firenze.i18n import Catalog, UnknownLocale, load
from firenze.interrogation import ask, confront
from firenze.interrogation.turn import MatchIsOver, NoTurnsLeft, UnknownEvidence
from firenze.model import ModelUnavailable, StructuredModel, resolve
from firenze.narration import write as narrate
from firenze.storage import (
    NotFound,
    engine,
    load_match,
    record_turn,
    save_match,
    start_match,
)
from firenze.verdict import (
    Accusation,
    AlreadyAccused,
    NotASuspect,
    Verdict,
    judge,
    verdict_of,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/matches", tags=["match"])


def connection() -> Iterator[Connection]:
    """A connection per request. **Committing is the handler's job.**

    It used to be this dependency's job — `with transaction()` here, commit on
    the way out. That reads well and is wrong, because FastAPI exits a
    dependency with `yield` only *after* the response has been sent: the client
    could be told the turn was taken, ask for the match, and get a connection of
    its own that opened before the commit landed.

    Which is exactly what the front end does after every question. The turn was
    charged and the answer was written, and the conversation came back without
    it — the question showed up only after the *next* one, together with it.

    So a write commits inside the handler, before the response exists. What
    keeps that honest is the test suite: it lets the API commit for real against
    a throwaway database, so a handler that forgets fails the next read.
    """
    with engine().connect() as open_connection:
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


def _plan(case: Case, catalog: Catalog) -> FloorPlan:
    """The house and the night. Never who was in which room."""
    return FloorPlan(
        rooms=tuple(Room(id=room, name=catalog.room(room)) for room in case.rooms),
        hours=tuple(
            Hour(interval=i, label=catalog.time(case.minutes_at(i)))
            for i in range(case.interval_count)
        ),
        crime_room=case.crime_room,
        crime_interval=case.crime_interval,
    )


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
                occupation=catalog.occupation(person.occupation) if person.occupation else None,
                stance=match.stances.get(person.id) if person.role is Role.suspect else None,
            )
            for person in case.cast
        ),
        known=tuple(
            KnownFact(id=fact.id, text=catalog.fact(case, fact))
            for fact in case.facts
            if fact.scope.public
        ),
        plan=_plan(case, catalog),
        evidence=tuple(sorted(match.evidence)),
        known_motives=known_motives(match),
        notebook=tuple(
            Said(
                turn=turn.turn,
                character=turn.character,
                question=turn.question,
                answered=turn.answered,
                line=turn.line or None,
                stance=turn.stance,
            )
            for turn in match.turns
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
    db.commit()
    return _state(match_id, load_match(db, match_id))


@router.get("/{match_id}", summary="The notebook")
def read(match_id: uuid.UUID, db: Db) -> MatchState:
    try:
        return _state(match_id, load_match(db, match_id))
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing


def _outcome(
    verdict: Verdict,
    accused: str,
    catalog: Catalog,
    turns_left: int,
    *,
    epilogue: str | None = None,
) -> Outcome:
    """The scoreboard, built in one place so a review cannot disagree with the
    ending the player was shown."""
    return Outcome(
        correct=verdict.correct,
        motive_correct=verdict.motive_correct,
        accused=accused,
        culprit=verdict.culprit,
        means=catalog.means(verdict.means_key),
        motive=catalog.motive(verdict.motive_key),
        score=verdict.score,
        culprit_points=verdict.culprit_points,
        motive_points=verdict.motive_points,
        evidence_points=verdict.evidence_points,
        speed_points=verdict.speed_points,
        evidence_expected=verdict.evidence_expected,
        evidence_hit=verdict.evidence_hit,
        turns_left=turns_left,
        epilogue=epilogue,
    )


def _review(match_id: uuid.UUID, match: Match) -> Review:
    """Build the review of a decided match. Reads the record, decides nothing."""
    case = match.case
    catalog = load(match.locale)

    record = tuple(
        ReviewedTurn(
            turn=turn.turn,
            cost=turn.cost,
            character=turn.character,
            character_name=case.name_of(turn.character),
            question=turn.question,
            intent=turn.intent.value,
            answered=turn.answered,
            line=turn.line or None,
            stance=turn.stance,
            rejected_by=turn.rejected_by,
            lied=turn.lied,
            fact_referenced=turn.fact_referenced,
            clue_revealed=turn.clue_revealed,
            claimed_room=turn.claimed_room,
            claimed_interval=turn.claimed_interval,
        )
        for turn in match.turns
    )

    # Walked rather than stored. A rejected turn records the stance the suspect
    # was already in, so it can never invent a move that did not happen.
    standing: dict[str, Stance] = {}
    trail: list[StanceMove] = []
    for turn in match.turns:
        before = standing.get(turn.character, Stance.cooperative)
        if turn.stance is not before:
            trail.append(
                StanceMove(
                    turn=turn.turn,
                    character=turn.character,
                    character_name=case.name_of(turn.character),
                    was=before,
                    became=turn.stance,
                )
            )
        standing[turn.character] = turn.stance

    given = {t.clue_revealed: t for t in match.statements if t.clue_revealed}
    held = tuple(
        HeldEvidence(
            id=fact.id,
            text=catalog.fact(case, fact),
            turn=given[fact.id].turn if fact.id in given else None,
            given_by=given[fact.id].character if fact.id in given else None,
            given_by_name=(case.name_of(given[fact.id].character) if fact.id in given else None),
        )
        for fact in case.facts
        if fact.id in match.evidence
    )

    verdict = verdict_of(match)
    budget = sum(turn.cost for turn in match.turns) + match.turns_left
    return Review(
        id=match_id,
        seed=case.seed,
        locale=match.locale,
        budget=budget,
        turns_left=match.turns_left,
        turns_spent=budget - match.turns_left,
        record=record,
        stance_trail=tuple(trail),
        evidence_trail=tuple(sorted(held, key=lambda e: (e.turn is not None, e.turn or 0, e.id))),
        outcome=_outcome(verdict, match.accused_culprit or "", catalog, match.turns_left),
    )


@router.get("/{match_id}/review", summary="The whole record of a finished match")
def review(match_id: uuid.UUID, db: Db) -> Review:
    """Every turn in order, the stances, the evidence, and the verdict.

    Only once the match is over, and that is the whole reason it may show the
    bookkeeping — `lied`, which fact an answer leaned on, what a rejected turn
    was rejected for. Offered mid-match the same payload would be a lie
    detector and end the game on turn one, so it is a 409 until there is
    nothing left to spoil (RN-035).
    """
    try:
        match = load_match(db, match_id)
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing

    if not match.is_over:
        raise HTTPException(status.HTTP_409_CONFLICT, "this match is still being played")

    return _review(match_id, match)


@router.post("/{match_id}/accusation/draft", summary="Read an accusation out of prose")
def draft_accusation(
    match_id: uuid.UUID, body: AccusationText, db: Db, model: Model
) -> DraftAccusation:
    """Fills the form; commits nothing.

    The player confirms by posting the fields to `/accusation`. That endpoint
    accepts no prose, so a misreading cannot become an accusation without
    somebody seeing it first (RN-031).
    """
    try:
        match = load_match(db, match_id)
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing

    if match.is_over:
        raise HTTPException(status.HTTP_409_CONFLICT, "this match has been decided")

    catalog = load(match.locale)
    try:
        draft = parse(match, catalog, body.text, model=model)
    except ModelUnavailable as unreachable:
        log.warning("could not read the accusation on match %s: %s", match_id, unreachable)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "the accusation could not be read; name the suspect directly instead",
        ) from unreachable

    return DraftAccusation(
        culprit=draft.culprit,
        culprit_name=match.case.name_of(draft.culprit) if draft.culprit else None,
        motive_key=draft.motive_key,
        motive=catalog.motive(draft.motive_key) if draft.motive_key else None,
        evidence=draft.evidence,
        evidence_text=tuple(catalog.fact(match.case, match.case.fact(e)) for e in draft.evidence),
        unresolved=draft.unresolved,
        summary=summarise(draft, match.case, catalog),
    )


@router.post("/{match_id}/accusation", summary="Name a culprit and end the match")
def accuse(match_id: uuid.UUID, body: NewAccusation, db: Db) -> Outcome:
    """No model is involved. The outcome is arithmetic (RN-032)."""
    try:
        match = load_match(db, match_id)
    except NotFound as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing

    try:
        verdict = judge(
            match,
            Accusation(
                culprit=body.culprit,
                motive_key=body.motive_key,
                evidence=body.evidence,
            ),
        )
    except AlreadyAccused as decided:
        raise HTTPException(status.HTTP_409_CONFLICT, str(decided)) from decided
    except NotASuspect as unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(unknown)) from unknown

    decided_match = match.model_copy(
        update={
            "accused_culprit": body.culprit,
            "accused_motive_key": body.motive_key,
            "accused_evidence": tuple(body.evidence),
        }
    )
    save_match(db, match_id, decided_match)
    db.commit()

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

    return _outcome(verdict, body.culprit, catalog, match.turns_left, epilogue=epilogue)


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

    record_turn(db, match_id, result.match, result.turn)
    db.commit()

    if not result.turn.answered:
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
        line=result.turn.line,
        stance=result.turn.stance,
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

    record_turn(db, match_id, result.match, result.turn)
    db.commit()

    if not result.turn.answered:
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
        line=result.turn.line,
        stance=result.turn.stance,
        turns_left=result.match.turns_left,
    )
