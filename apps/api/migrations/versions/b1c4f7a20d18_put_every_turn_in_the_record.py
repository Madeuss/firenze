"""put every turn in the record

A rejected turn — canary, contradiction, scope, refusal — spent budget and left
no row. `statements` becomes `turns` because that is what it now holds: a row
with no `line` is the account of a turn that produced nothing.

Revision ID: b1c4f7a20d18
Revises: ecc6ce9e9e22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c4f7a20d18'
down_revision: str | None = 'ecc6ce9e9e22'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table('statements', 'turns')
    op.execute('ALTER TABLE turns RENAME CONSTRAINT uq_statements_turn TO uq_turns_turn')
    op.add_column('turns', sa.Column('rejected_by', sa.String(length=32), nullable=True))
    op.add_column('turns', sa.Column('cost', sa.Integer(), server_default='1', nullable=False))
    # Rows written before this point are all answers, so the existing values
    # stay as they are; the default only covers rows written from now on.
    op.alter_column('turns', 'line', server_default='')


def downgrade() -> None:
    # A rejected turn has no line, and there is nowhere to put it in the old
    # shape. Dropping those rows is the only honest reversal.
    op.execute("DELETE FROM turns WHERE rejected_by IS NOT NULL")
    op.alter_column('turns', 'line', server_default=None)
    op.drop_column('turns', 'cost')
    op.drop_column('turns', 'rejected_by')
    op.execute('ALTER TABLE turns RENAME CONSTRAINT uq_turns_turn TO uq_statements_turn')
    op.rename_table('turns', 'statements')
