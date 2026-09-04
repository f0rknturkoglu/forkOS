"""LinkedIn Connections.csv icin yerel profesyonel baglanti tablosu (kural 10)."""

from alembic import op

revision = "0045_career_connections"
down_revision = "0044_career_story_salary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """create table career_connection (
            id uuid primary key references entity(id) on delete cascade,
            identity_key text not null,
            first_name text null,
            last_name text null,
            profile_url text null,
            email text null,
            company text null,
            normalized_company text null,
            position text null,
            connected_on date null,
            constraint career_connection_identity_key_uniq unique (identity_key)
        )"""
    )
    op.execute(
        "create index career_connection_normalized_company_idx "
        "on career_connection(normalized_company)"
    )


def downgrade() -> None:
    op.execute("drop index career_connection_normalized_company_idx")
    op.execute("drop table career_connection")
