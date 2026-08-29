"""İş kategorisini başlık ve departman sinyaline öncelik vererek düzelt.

Her SQL komutu ayrı op.execute() çağrısı kullanır (kural 10).
"""

from alembic import op

revision = "0032_refine_categories"
down_revision = "0031_osym_publication_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    signal = (
        "immutable_unaccent(lower(e.title || ' ' || "
        "coalesce(o.raw->'forkjob'->>'department', "
        "o.raw->>'department', '')))"
    )
    data_ai = (
        "machine learning|data scientist|data engineer|ai engineer|ml engineer|"
        "mlops|artificial intelligence|yapay zeka"
    )
    cloud = "devops|site reliability|platform engineer|cloud|cyber|security|guvenlik"
    product = "product manager|product designer|product owner|user experience|ui designer"
    software = (
        "software|developer|engineer|backend|frontend|full.?stack|mobile|"
        "quality assurance|tester|yazilim|bilisim"
    )
    sales = (
        "sales|marketing|account manager|business development|growth manager|"
        "satis|pazarlama"
    )
    operations = (
        "operations|finance|financial|legal|human resources|customer support|"
        "customer success|operasyon|finans"
    )
    statement = (
        "update opportunity o set category = case "
        f"when {signal} ~ '({data_ai})' then 'data-ai' "
        f"when {signal} ~ '({cloud})' then 'cloud-security' "
        f"when {signal} ~ '({product})' then 'product-design' "
        f"when {signal} ~ '({software})' then 'software' "
        f"when {signal} ~ '({sales})' then 'sales-marketing' "
        f"when {signal} ~ '({operations})' then 'business-ops' "
        "else 'other' end from entity e where e.id = o.id and o.kind = 'job'"
    )
    op.execute(statement)


def downgrade() -> None:
    op.execute(
        "update opportunity set category = coalesce(category, 'other') where kind = 'job'"
    )
