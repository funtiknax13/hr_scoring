"""scoring_jobs: add is_eval, expected_scores, eval_tau

Revision ID: 005
Revises: 004
Create Date: 2026-06-21
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scoring_jobs", sa.Column("is_eval", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("scoring_jobs", sa.Column("expected_scores", sa.Text(), nullable=True))
    op.add_column("scoring_jobs", sa.Column("eval_tau", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("scoring_jobs", "eval_tau")
    op.drop_column("scoring_jobs", "expected_scores")
    op.drop_column("scoring_jobs", "is_eval")
