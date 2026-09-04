"""career story bank and interview salary claims

Revision ID: 0044_career_story_salary
Revises: 0043_opportunity_evaluation
"""

from alembic import op

revision = "0044_career_story_salary"
down_revision = "0043_opportunity_evaluation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """create table career_story (
            id uuid primary key references entity(id) on delete cascade,
            situation text null,
            task text null,
            action text null,
            result text null,
            reflection text null,
            provenance text not null default 'existing',
            tags jsonb not null default '[]'::jsonb,
            constraint ck_career_story_provenance check (
                provenance in ('existing', 'supported', 'derived-unverified', 'user-cannot-confirm')
            )
        )"""
    )
    op.execute("alter table interview add column salary_stated text null")


def downgrade() -> None:
    op.execute("alter table interview drop column salary_stated")
    op.execute("drop table career_story")
