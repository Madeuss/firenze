"""Reading and writing matches.

Two methods load a case, and which one you call decides what you are allowed to
know:

    load_case(case_id)  -> Case              # no solution reachable
    load_match(match_id) -> Match            # solution included, for the verdict

That is the same boundary as everywhere else in this project, expressed once
more in the layer where it is easiest to lose (RN-011). A caller that only needs
to render a briefing takes the first and physically cannot obtain the culprit —
the query does not touch the table it lives in.

A turn is one transaction: the statement, the stance and the budget move
together or not at all. Splitting them would let a crash leave a match that was
charged for an answer it never recorded (RN-030).
"""

import uuid

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from firenze.domain import Case, CaseWithSolution, Match, Solution, Stance, Statement
from firenze.storage.tables import cases, matches, solutions, statements


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
        select(matches.c.case_id, matches.c.locale, matches.c.turns_left, matches.c.stances).where(
            matches.c.id == match_id
        )
    ).first()
    if row is None:
        raise NotFound(f"no match {match_id}")

    said = connection.execute(
        select(
            statements.c.turn,
            statements.c.character,
            statements.c.question,
            statements.c.line,
            statements.c.stance,
            statements.c.lied,
            statements.c.fact_referenced,
        )
        .where(statements.c.match_id == match_id)
        .order_by(statements.c.turn)
    ).all()

    return Match(
        full_case=load_full_case(connection, uuid.UUID(str(row[0]))),
        locale=row[1],
        turns_left=row[2],
        stances={who: Stance(value) for who, value in (row[3] or {}).items()},
        statements=tuple(
            Statement(
                turn=s[0],
                character=s[1],
                question=s[2],
                line=s[3],
                stance=Stance(s[4]),
                lied=s[5],
                fact_referenced=s[6],
            )
            for s in said
        ),
    )


def record_turn(
    connection: Connection,
    match_id: uuid.UUID,
    match: Match,
    statement: Statement | None,
) -> None:
    """Persist what one turn changed, in one transaction.

    `statement` is None when the reply was rejected — the budget still moves,
    because a turn that only charged for answers the system liked would be a
    turn a player could farm by provoking failures.
    """
    connection.execute(
        update(matches)
        .where(matches.c.id == match_id)
        .values(
            turns_left=match.turns_left,
            stances={who: stance.value for who, stance in match.stances.items()},
        )
    )
    if statement is None:
        return

    connection.execute(
        insert(statements).values(
            id=uuid.uuid4(),
            match_id=match_id,
            turn=statement.turn,
            character=statement.character,
            question=statement.question,
            line=statement.line,
            stance=statement.stance.value,
            lied=statement.lied,
            fact_referenced=statement.fact_referenced,
        )
    )
