"""schedule: scheduled_searches, scheduled_search_logs

Revision ID: 004
Revises: 003
Create Date: 2026-06-21
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


logstatus = sa.Enum("running", "done", "error", name="logstatus")


def upgrade() -> None:
    op.create_table(
        "scheduled_searches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("query", sa.String, nullable=False),
        sa.Column("city", sa.String, nullable=True),
        sa.Column("max_pages", sa.Integer, nullable=False, server_default="3"),
        sa.Column("cron", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "scheduled_search_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("search_id", sa.Integer, sa.ForeignKey("scheduled_searches.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", logstatus, nullable=False),
        sa.Column("vacancies_found", sa.Integer, nullable=True),
        sa.Column("error", sa.String, nullable=True),
        sa.Column("fetch_session_id", sa.Integer, sa.ForeignKey("fetch_sessions.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scheduled_search_logs")
    op.drop_table("scheduled_searches")
    logstatus.drop(op.get_bind())
