"""Gelir kaydi (income) -- gelir/gider dengesi icin.

PK entity.id'ye FK (kural 1); baslik Entity.title'da yasar.
Her SQL komutu ayri op.execute() (kural 10).
"""

from alembic import op

revision = "0033_finance_income"
down_revision = "0032_refine_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table income (
            id uuid primary key references entity(id) on delete cascade,
            amount numeric(12,2) not null,
            currency char(3) not null default 'TRY',
            category text not null default 'salary',
            received_on date not null default current_date,
            note text
        )
    """)
    op.execute("create index income_month_idx on income (received_on desc, category)")


def downgrade() -> None:
    op.execute("drop index if exists income_month_idx")
    op.execute("drop table income")
