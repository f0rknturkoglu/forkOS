"""H7.1: yürütücü lease'i (kalp atışı) ve makbuz durum ayrımı.

Revision ID: 0062_execution_recovery
Revises: 0061_execution
Create Date: 2026-09-21

Neden:

1) `execution_plan.executor_token` + `execution_started_at` canlı bir süreçle
   çökmüş bir süreci AYIRT EDEMİYORDU: plan sonsuza dek `executing` kalıyor ve
   genel yüzeyden kurtarılamıyordu. Kalp atışı (heartbeat) eklendi; lease
   bayatlarsa plan ATOMİK olarak devralınabilir.
2) `execution_receipt.status` iki FARKLI durumu tek değerde birleştiriyordu:
   "hiç denenmedi" ile "mutasyon olmuş OLABİLİR, mutabakat gerekli". Bunlar
   operasyonel olarak aynı şey değildir; ayrı değer eklendi.
"""

from alembic import op

revision = "0062_execution_recovery"
down_revision = "0061_execution"
branch_labels = None
depends_on = None

UPGRADE = [
    "alter table execution_plan add column execution_heartbeat_at timestamptz",
    # Kanit durumu: hangi referans GERCEKTEN dogrulandi (H7.1/F).
    "alter table execution_plan add column verified_refs jsonb not null default '[]'::jsonb",
    "alter table execution_plan add column unresolved_refs jsonb not null default '[]'::jsonb",
    # Bayat lease taraması ve kurtarma sahipliği bu indeksi kullanır.
    """
    create index ix_execution_plan_executing on execution_plan (execution_heartbeat_at)
      where state = 'executing'
    """,
    # Makbuz durum kümesine "mutabakat gerekli" eklendi.
    "alter table execution_receipt drop constraint execution_receipt_status_valid",
    """
    alter table execution_receipt add constraint execution_receipt_status_valid
      check (status in ('completed', 'failed', 'not_attempted', 'unresolved'))
    """,
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("alter table execution_receipt drop constraint execution_receipt_status_valid")
    op.execute(
        "alter table execution_receipt add constraint execution_receipt_status_valid "
        "check (status in ('completed', 'failed', 'skipped', 'not_attempted'))"
    )
    op.execute("alter table execution_plan drop column if exists unresolved_refs")
    op.execute("alter table execution_plan drop column if exists verified_refs")
    op.execute("drop index if exists ix_execution_plan_executing")
    op.execute("alter table execution_plan drop column if exists execution_heartbeat_at")
