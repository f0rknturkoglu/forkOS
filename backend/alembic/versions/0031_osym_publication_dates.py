"""Mevcut ÖSYM duyurularının başlıktaki resmi yayın tarihini çıkar.

Her SQL komutu ayrı op.execute() çağrısı kullanır (kural 10).
"""

from alembic import op

revision = "0031_osym_publication_dates"
down_revision = "0030_opportunity_category_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "update opportunity o set published_at = make_timestamptz("
        "split_part(e.title, ' ', 3)::integer, "
        "case immutable_unaccent(lower(split_part(e.title, ' ', 2))) "
        "when 'ocak' then 1 when 'subat' then 2 when 'mart' then 3 "
        "when 'nisan' then 4 when 'mayis' then 5 when 'haziran' then 6 "
        "when 'temmuz' then 7 when 'agustos' then 8 when 'eylul' then 9 "
        "when 'ekim' then 10 when 'kasim' then 11 when 'aralik' then 12 end, "
        "split_part(e.title, ' ', 1)::integer, 0, 0, 0, 'UTC') "
        "from entity e where e.id = o.id and o.source = 'osym' "
        "and o.published_at is null "
        "and e.title ~ '^[0-9]{1,2} [[:alpha:]ÇĞİÖŞÜçğıöşü]+ [0-9]{4} ' "
        "and immutable_unaccent(lower(split_part(e.title, ' ', 2))) "
        "in ('ocak','subat','mart','nisan','mayis','haziran','temmuz','agustos','eylul','ekim','kasim','aralik')"
    )


def downgrade() -> None:
    op.execute(
        "update opportunity set published_at = null where source = 'osym' "
        "and coalesce(raw->>'published_at', '') = ''"
    )
