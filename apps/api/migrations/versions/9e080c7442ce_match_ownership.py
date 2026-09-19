"""match ownership

A match had no owner, so anyone holding its id could read its notebook, spend
its turns and accuse in its name (T-11). The column holds a SHA-256 of the
token handed to whoever created the match, never the token: a dump of this
table gives up nobody's game.

Nullable because matches created before this column exists still have to load.
On a guarded deployment they are unreachable, which is the only answer that
cannot be wrong about who they belong to.

Revision ID: 9e080c7442ce
Revises: c7d1e0a94f52
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "9e080c7442ce"
down_revision: str | None = "c7d1e0a94f52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("owner_token_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "owner_token_hash")
