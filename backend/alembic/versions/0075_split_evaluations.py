"""Separate candidate and deep evaluations while preserving legacy payloads."""

from alembic import op
from sqlalchemy import text

revision = "0075_split_evaluations"
down_revision = "0074_forkjob_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table opportunity add column candidate_evaluation jsonb")
    op.execute("alter table opportunity add column candidate_evaluated_at timestamptz")
    op.execute("alter table opportunity add column deep_evaluation jsonb")
    op.execute("alter table opportunity add column deep_evaluated_at timestamptz")
    op.execute(
        """update opportunity set
            deep_evaluation = evaluation,
            deep_evaluated_at = evaluated_at
           where evaluation ? 'candidate_context_revision'
             and evaluation ? 'overall_assessment'"""
    )
    op.execute(
        """update opportunity set
            candidate_evaluation = evaluation,
            candidate_evaluated_at = evaluated_at
           where evaluation ? 'score'
             and evaluation ? 'recommendation'
             and evaluation ? 'requirements'
             and deep_evaluation is null"""
    )


def downgrade() -> None:
    # Refuse to discard evaluations written only after this split. Existing
    # migrated payloads still match the untouched legacy column exactly.
    divergent = op.get_bind().execute(
        text(
            """select exists (
                select 1 from opportunity
                where (candidate_evaluation is not null
                       and candidate_evaluation <> '{}'::jsonb
                       and candidate_evaluation <> evaluation)
                   or (deep_evaluation is not null
                       and deep_evaluation <> '{}'::jsonb
                       and deep_evaluation <> evaluation)
            )"""
        )
    ).scalar_one()
    if divergent:
        raise RuntimeError("Cannot downgrade: split evaluations contain newer data")
    op.execute("alter table opportunity drop column deep_evaluated_at")
    op.execute("alter table opportunity drop column deep_evaluation")
    op.execute("alter table opportunity drop column candidate_evaluated_at")
    op.execute("alter table opportunity drop column candidate_evaluation")
