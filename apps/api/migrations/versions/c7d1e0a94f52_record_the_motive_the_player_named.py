"""record the motive the player named

The verdict is derived, never stored (RN-032). Without the accused motive the
record could not reproduce the score a review is supposed to show.

Revision ID: c7d1e0a94f52
Revises: b1c4f7a20d18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c7d1e0a94f52"
down_revision: str | None = "b1c4f7a20d18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("accused_motive", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "accused_motive")
