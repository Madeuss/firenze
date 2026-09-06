# ADR-0009: A case is a document, a match is rows

## Status

Accepted — 2026-08-31

## Context

Matches have to survive a restart before there is an HTTP endpoint worth
writing, and before NPC memory can live in the same transaction as game state —
which is the whole argument of ADR-0002.

The two things being stored are not alike.

A **case** is generated from a seed, validated once, and then immutable. It is
always read whole: a briefing needs the cast, the facts and the timeline
together, and nothing ever queries "all facts in the cellar across every case".
Its shape also moves — the generator gained `setting` days after it gained
`interval_count`.

A **match** is the opposite. Turns accumulate one at a time, statements are read
back per character to find contradictions (RN-021), and the budget changes on
every turn under whatever concurrency the future brings.

## Decision

**The case is a document.** One `cases` row with a JSONB column, plus the three
columns that identify it — seed, generator version, setting — as real columns
with a unique constraint over them. Normalising facts and cast into tables would
buy joins nobody performs and a migration every time the generator learns a new
field.

**The match is relational.** `matches` and `statements` are ordinary tables with
foreign keys, because they are appended to, queried by character, and updated
under contention.

**The solution gets its own table.** `Case` and `Solution` are separate entities
so that isolation is a type signature rather than a discipline (RN-011). The
same argument applies to storage: as a column on `cases`, the culprit would ride
along in every `SELECT *`, and the guarantee would last exactly as long as
nobody wrote a convenient query. In its own table, `load_case` **cannot** return
it — the read does not touch where it lives.

**SQLAlchemy Core, synchronously.** Core rather than the ORM because these are
five queries over four tables and Pydantic already owns the domain objects; an
ORM would add a second object model to keep in agreement with the first.
Synchronous because the slow thing in a turn is the model call, not the
database, and FastAPI runs sync endpoints in a threadpool — an async driver
would add a second execution model to reason about for a saving that does not
show up at one player per match.

**Storage tests run against Postgres**, in CI as a service container. A schema
using JSONB and a composite unique constraint, tested on SQLite, proves the
tests pass.

## Consequences

+ The case round-trips exactly, canary tokens and all, so a stored match
  reproduces the mystery it started from.
+ The generator can gain fields without a migration.
+ Isolation survives into the persistence layer, where it is easiest to lose.
+ One transaction covers the statement, the stance and the budget, so a crash
  cannot leave a match charged for an answer it never recorded (RN-030).
+ NPC memory can join match state in the same transaction when it arrives, which
  is the reason ADR-0002 chose one database.
− A JSONB case is opaque to SQL: "which cases put someone in the cellar at
  22:00" is a scan, not an index. Acceptable while nothing asks; a generated
  column would be the answer if something does.
− No schema validation on the document. A case written by an older generator
  deserialises into whatever the current models accept, and `generator_version`
  is what makes that detectable rather than silent.
− Synchronous I/O will need revisiting if a single process ever serves many
  concurrent matches. The store is small enough that this is a rewrite of one
  module.
− CI now needs a database service, which costs seconds per run and a moving part
  that can fail on its own.

## Alternatives considered

- **Fully normalised, facts and cast as tables.** The obvious relational answer,
  and it would make the case queryable. Rejected because nothing queries it: the
  access pattern is "load this whole case", and the price is a migration for
  every field the generator gains — which, at one generator change per week
  lately, is the wrong side of the trade.
- **Documents all the way, matches in JSONB too.** Simplest to write and wrong
  by the second concurrent turn: appending a statement would mean read, modify,
  write, and losing one under a race.
- **SQLModel.** One class serving as both Pydantic model and table. Attractive
  until the domain model wants to be frozen, computed and free of persistence
  concerns — which this one is, deliberately.
- **Async SQLAlchemy with asyncpg.** The default reflex for FastAPI. Deferred:
  it buys concurrency the workload does not have yet, at the cost of a second
  execution model in every test and CLI path.
