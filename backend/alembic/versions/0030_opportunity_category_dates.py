"""Firsat kategorisi ve gercek yayin tarihi.

Her SQL komutu ayri op.execute() cagrisi kullanir (kural 10).
"""

from alembic import op

revision = "0030_opportunity_category_dates"
down_revision = "0029_project_journal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table opportunity add column category text")
    op.execute("alter table opportunity add column published_at timestamptz")
    op.execute(
        "update opportunity set published_at = (raw->>'published_at')::timestamptz "
        "where coalesce(raw->>'published_at', '') ~ '^\\d{4}-\\d{2}-\\d{2}T'"
    )
    op.execute(
        "update opportunity o set category = case "
        "when immutable_unaccent(lower(e.title || ' ' || coalesce(o.organization, '') || ' ' || coalesce(o.raw::text, ''))) "
        "~ '(machine learning|data scientist|data engineer|ai engineer|ml engineer|mlops|artificial intelligence|yapay zeka)' then 'data-ai' "
        "when immutable_unaccent(lower(e.title || ' ' || coalesce(o.organization, '') || ' ' || coalesce(o.raw::text, ''))) "
        "~ '(devops|site reliability|platform engineer|cloud|cyber|security|guvenlik)' then 'cloud-security' "
        "when immutable_unaccent(lower(e.title || ' ' || coalesce(o.organization, '') || ' ' || coalesce(o.raw::text, ''))) "
        "~ '(product manager|product designer|product owner|user experience|ui designer)' then 'product-design' "
        "when immutable_unaccent(lower(e.title || ' ' || coalesce(o.organization, '') || ' ' || coalesce(o.raw::text, ''))) "
        "~ '(software|developer|engineer|backend|frontend|full.?stack|mobile|quality assurance|tester|yazilim|bilisim)' then 'software' "
        "when immutable_unaccent(lower(e.title || ' ' || coalesce(o.organization, '') || ' ' || coalesce(o.raw::text, ''))) "
        "~ '(sales|marketing|account manager|business development|growth manager|satis|pazarlama)' then 'sales-marketing' "
        "when immutable_unaccent(lower(e.title || ' ' || coalesce(o.organization, '') || ' ' || coalesce(o.raw::text, ''))) "
        "~ '(operations|finance|financial|legal|human resources|customer support|customer success|operasyon|finans)' then 'business-ops' "
        "else 'other' end from entity e where e.id = o.id and o.kind = 'job'"
    )
    op.execute("create index opportunity_category_idx on opportunity(category)")
    op.execute("create index opportunity_published_at_idx on opportunity(published_at desc)")


def downgrade() -> None:
    op.execute("drop index opportunity_published_at_idx")
    op.execute("drop index opportunity_category_idx")
    op.execute("alter table opportunity drop column published_at")
    op.execute("alter table opportunity drop column category")
