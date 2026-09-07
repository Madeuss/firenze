"""Reading and writing matches.

Two methods load a case, and which one you call decides what you are allowed to
know:

    load_case(case_id)  -> Case              # no solution reachable
    load_match(match_id) -> Match            # solution included, for the verdict

That is the same boundary as everywhere else in this project, expressed once
more in the layer where it is easiest to lose (RN-011). A caller that only needs
to render a briefing takes the first and physically cannot obtain the culprit —
the query does not touch the table it lives in.

A turn is one transaction: the turn, the stance and the budget move together or
not at all. Splitting them would let a crash leave a match that was charged for
an answer it never recorded (RN-030). Every turn is written, answered or not —
a budget that only recorded successes could not explain where it went.
"""

import uuid

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from firenze.domain import (
    Case,
    CaseWithSolution,
    Intent,
    Match,
    Solution,
    Stance,
    Turn,
)
from firenze.storage.tables import cases, matches, solutions
from firenze.storage.tables import turns as turns_table


class NotFound(LookupError):
    """No row with that id."""


def save_case(connection: Connection, full: CaseWithSolution) -> uuid.UUID:
    """Store a case and its solution. Idempotent on the case's identity."""
    case = full.case
    existing = connection.execute(
        select(cases.c.id).where(
            cases.c.seed == case.seed,
            cases.c.generator_version == case.generator_version,
            cases.c.setting == case.setting,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return uuid.UUID(str(existing))

    case_id = uuid.uuid4()
    connection.execute(
        insert(cases).values(
            id=case_id,
            seed=case.seed,
            generator_version=case.generator_version,
            setting=case.setting,
            document=case.model_dump(mode="json"),
        )
    )
    connection.execute(
        insert(solutions).values(case_id=case_id, document=full.solution.model_dump(mode="json"))
    )
    return case_id


def load_case(connection: Connection, case_id: uuid.UUID) -> Case:
    """The case as a player's side of the system may know it. No solution."""
    row = connection.execute(
        select(cases.c.document).where(cases.c.id == case_id)
    ).scalar_one_or_none()
    if row is None:
        raise NotFound(f"no case {case_id}")
    return Case.model_validate(row)


def load_full_case(connection: Connection, case_id: uuid.UUID) -> CaseWithSolution:
    """Case plus solution. For the generator, the solver and the verdict."""
    row = connection.execute(
        select(cases.c.document, solutions.c.document)
        .join(solutions, solutions.c.case_id == cases.c.id)
        .where(cases.c.id == case_id)
    ).first()
    if row is None:
        raise NotFound(f"no case {case_id}")
    return CaseWithSolution(
        case=Case.model_validate(row[0]), solution=Solution.model_validate(row[1])
    )


def start_match(connection: Connection, full: CaseWithSolution, locale: str) -> uuid.UUID:
    """Save the case if needed and open a match on it."""
    case_id = save_case(connection, full)
    match_id = uuid.uuid4()
    connection.execute(
        insert(matches).values(
            id=match_id,
            case_id=case_id,
            locale=locale,
            turns_left=Match.model_fields["turns_left"].default,
            stances={},
        )
    )
    return match_id


def load_match(connection: Connection, match_id: uuid.UUID) -> Match:
    row = connection.execute(
        select(
            matches.c.case_id,
            matches.c.locale,
            matches.c.turns_left,
            matches.c.stances,
            matches.c.accused_culprit,
            matches.c.accused_evidence,
        ).where(matches.c.id == match_id)
    ).first()
    if row is None:
        raise NotFound(f"no match {match_id}")

    record = connection.execute(
        select(
            turns_table.c.turn,
            turns_table.c.character,
            turns_table.c.question,
            turns_table.c.line,
            turns_table.c.stance,
            turns_table.c.lied,
            turns_table.c.rejected_by,
            turns_table.c.cost,
            turns_table.c.fact_referenced,
            turns_table.c.claimed_room,
            turns_table.c.claimed_interval,
            turns_table.c.clue_revealed,
            turns_table.c.intent,
        )
        .where(turns_table.c.match_id == match_id)
        .order_by(turns_table.c.turn)
    ).all()

    return Match(
        full_case=load_full_case(connection, uuid.UUID(str(row[0]))),
        locale=row[1],
        turns_left=row[2],
        stances={who: Stance(value) for who, value in (row[3] or {}).items()},
        accused_culprit=row[4],
        accused_evidence=tuple(row[5] or ()),
        turns=tuple(
            Turn(
                turn=t[0],
                character=t[1],
                question=t[2],
                line=t[3],
                stance=Stance(t[4]),
                lied=t[5],
                rejected_by=t[6],
                cost=t[7],
                fact_referenced=t[8],
                claimed_room=t[9],
                claimed_interval=t[10],
                clue_revealed=t[11],
                intent=Intent(t[12]),
            )
            for t in record
        ),
    )


def save_match(connection: Connection, match_id: uuid.UUID, match: Match) -> None:
    """Persist the state of a match without recording a turn.

    For the one thing that changes a match and is not a turn: an accusation
    ends it and costs no budget (RN-031).
    """
    connection.execute(
        update(matches)
        .where(matches.c.id == match_id)
        .values(
            turns_left=match.turns_left,
            stances={who: stance.value for who, stance in match.stances.items()},
            accused_culprit=match.accused_culprit,
            accused_evidence=list(match.accused_evidence),
        )
    )


def record_turn(
    connection: Connection,
    match_id: uuid.UUID,
    match: Match,
    turn: Turn,
) -> None:
    """Persist what one turn changed, in one transaction.

    A rejected turn is written like any other, with no line and the name of the
    check that discarded it. The budget moved either way — a turn that only
    charged for answers the system liked would be a turn a player could farm by
    provoking failures — and the record has to be able to say so.
    """
    save_match(connection, match_id, match)
    connection.execute(
        insert(turns_table).values(
            id=uuid.uuid4(),
            match_id=match_id,
            turn=turn.turn,
            character=turn.character,
            question=turn.question,
            line=turn.line,
            stance=turn.stance.value,
            lied=turn.lied,
            rejected_by=turn.rejected_by,
            cost=turn.cost,
            fact_referenced=turn.fact_referenced,
            claimed_room=turn.claimed_room,
            claimed_interval=turn.claimed_interval,
            clue_revealed=turn.clue_revealed,
            intent=turn.intent.value,
        )
    )
