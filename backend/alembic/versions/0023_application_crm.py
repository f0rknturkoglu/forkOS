"""Application CRM: application, history, interview; follow-up & region on opportunity."""

from alembic import op

revision = "0023_application_crm"
down_revision = "0022_finance_sub"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Opportunity: bolge filtreleri, takip tarihi, red nedeni
    op.execute("alter table opportunity add column country text")
    op.execute("alter table opportunity add column region text")
    op.execute("alter table opportunity add column follow_up_at timestamptz")
    op.execute("alter table opportunity add column rejection_reason text")
    op.execute(
        "create index opportunity_followup_idx on opportunity (follow_up_at) "
        "where follow_up_at is not null"
    )

    # Basvuru kaydi (1:1) -- PK entity FK (kural 1)
    op.execute(
        """create table application (
          opportunity_id uuid primary key references entity(id) on delete cascade,
          cv_document_id uuid references entity(id) on delete set null,
          cv_title text,
          cv_modified_at timestamptz,
          cover_letter text,
          company_research text,
          salary_expectation text,
          posting_snapshot jsonb not null default ' {}'::jsonb,
          note text,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )"""
    )

    # Durum gecis gecmisi (append-only)
    op.execute(
        """create table application_history (
          id uuid primary key default gen_random_uuid(),
          opportunity_id uuid not null references opportunity(id) on delete cascade,
          from_status text,
          to_status text not null,
          at timestamptz not null default now(),
          note text
        )"""
    )
    op.execute(
        "create index application_history_opp_idx on application_history "
        "(opportunity_id, at desc)"
    )

    # Gorusmeler (coklu)
    op.execute(
        """create table interview (
          id uuid primary key default gen_random_uuid(),
          opportunity_id uuid not null references opportunity(id) on delete cascade,
          stage text not null default 'genel',
          mode text,
          scheduled_at timestamptz,
          duration_min int,
          notes text,
          outcome text,
          position int not null default 0
        )"""
    )
    op.execute("create index interview_opp_idx on interview (opportunity_id, position)")


def downgrade() -> None:
    op.execute("drop table if exists interview")
    op.execute("drop index if exists application_history_opp_idx")
    op.execute("drop table if exists application_history")
    op.execute("drop table if exists application")
    op.execute("drop index if exists opportunity_followup_idx")
    op.execute("alter table opportunity drop column if exists rejection_reason")
    op.execute("alter table opportunity drop column if exists follow_up_at")
    op.execute("alter table opportunity drop column if exists region")
    op.execute("alter table opportunity drop column if exists country")
