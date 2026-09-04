"""CV eslesme oranini hizli filtreleme ve siralama icin sakla."""

from alembic import op

revision = "0046_skill_match_ratio"
down_revision = "0045_career_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table opportunity add column skill_match_ratio double precision null")
    op.execute(
        "alter table opportunity add constraint opportunity_skill_match_ratio_range "
        "check (skill_match_ratio is null or (skill_match_ratio >= 0 and skill_match_ratio <= 1))"
    )
    op.execute(
        "create index opportunity_skill_match_ratio_idx "
        "on opportunity(skill_match_ratio desc) "
        "where kind = 'job' and trashed_at is null"
    )


def downgrade() -> None:
    op.execute("drop index opportunity_skill_match_ratio_idx")
    op.execute("alter table opportunity drop constraint opportunity_skill_match_ratio_range")
    op.execute("alter table opportunity drop column skill_match_ratio")
