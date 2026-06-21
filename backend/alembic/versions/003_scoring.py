"""scoring: vacancies, candidates, jobs, results

Revision ID: 003
Revises: 002
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scoring_vacancies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("text_hash", name="uq_scoring_vacancy_hash"),
    )
    op.create_index("ix_scoring_vacancies_text_hash", "scoring_vacancies", ["text_hash"])

    op.create_table(
        "scoring_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("resume_text", sa.Text(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("text_hash", name="uq_scoring_candidate_hash"),
    )
    op.create_index("ix_scoring_candidates_text_hash", "scoring_candidates", ["text_hash"])

    op.create_table(
        "scoring_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vacancy_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "done", "error", name="jobstatus"), nullable=False),
        sa.Column("rubric_json", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("prompt_versions", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["vacancy_id"], ["scoring_vacancies.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scoring_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("vacancy_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "done", "skipped", "error", name="resultstatus"), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("manipulation_attempt", sa.Boolean(), nullable=True),
        sa.Column("profile_json", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["scoring_jobs.id"]),
        sa.ForeignKeyConstraint(["vacancy_id"], ["scoring_vacancies.id"]),
        sa.ForeignKeyConstraint(["candidate_id"], ["scoring_candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("scoring_results")
    op.drop_table("scoring_jobs")
    op.drop_table("scoring_candidates")
    op.drop_table("scoring_vacancies")
    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS resultstatus")
