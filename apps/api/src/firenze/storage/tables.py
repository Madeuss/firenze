"""The schema.

Two shapes of data, stored differently on purpose.

**A case is a document.** It is generated, immutable once published, and only
ever read whole. Normalising facts and cast into tables would buy joins nobody
needs and a migration every time the generator gains a field. It goes in JSONB.

**A match is relational.** Turns accumulate, statements are queried per
character to find contradictions (RN-021), and budgets change under
concurrency. Those are rows.

## Why the solution has its own table

`Case` and `Solution` are separate entities so that isolation is a type
signature rather than a discipline (RN-011). The same argument applies one layer
down: if the solution were a column on `cases`, every `SELECT *` would carry the
culprit, and the guarantee would hold only as long as nobody wrote a convenient
query. In its own table, a read of `cases` **cannot** return it.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

# JSONB on Postgres, plain JSON elsewhere, so the schema stays readable in a
# SQLite session without pretending SQLite is what production runs.
JSON_DOC = JSON().with_variant(JSONB(), "postgresql")
UUID_PK = UUID(as_uuid=True).with_variant(String(36), "sqlite")

cases = Table(
    "cases",
    metadata,
    Column("id", UUID_PK, primary_key=True),
    Column("seed", Integer, nullable=False),
    Column("generator_version", String(16), nullable=False),
    Column("setting", String(64), nullable=False),
    Column("document", JSON_DOC, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Seed alone does not identify a case; these three together do.
    UniqueConstraint("seed", "generator_version", "setting", name="uq_cases_identity"),
)

solutions = Table(
    "solutions",
    metadata,
    Column("case_id", UUID_PK, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("document", JSON_DOC, nullable=False),
)

matches = Table(
    "matches",
    metadata,
    Column("id", UUID_PK, primary_key=True),
    Column("case_id", UUID_PK, ForeignKey("cases.id"), nullable=False),
    Column("locale", String(16), nullable=False),
    Column("turns_left", Integer, nullable=False),
    Column("stances", JSON_DOC, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

statements = Table(
    "statements",
    metadata,
    Column("id", UUID_PK, primary_key=True),
    Column("match_id", UUID_PK, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
    Column("turn", Integer, nullable=False),
    Column("character", String(32), nullable=False),
    Column("question", Text, nullable=False),
    Column("line", Text, nullable=False),
    Column("stance", String(16), nullable=False),
    Column("lied", Boolean, nullable=False),
    Column("fact_referenced", String(16), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Contradiction detection reads one character's statements within one match,
    # never across matches and never across characters (RN-013, RN-021).
    UniqueConstraint("match_id", "turn", name="uq_statements_turn"),
)

__all__ = ["cases", "matches", "metadata", "solutions", "statements"]
