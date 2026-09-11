"""Basvuru gecmisi kapsami ve cluster_key lookup index'i.

0050 kesif/basvuru/duyuru durumlarini ayirdi ve `application_history` artik iki
donguyu birden tasiyor. `scope` kolonu kaydin hangi makineye ait oldugunu
soyler; timeline ve funnel bu ayrimi kullanir.

Ikinci olarak ingest'teki cluster_key aramasi kayit basina JSONB taramasi
yapiyordu; ifade index'i tek sorguluk toplu lookup'i mümkün kilar.
"""

from alembic import op

revision = "0051_opportunity_history_scope"
down_revision = "0050_opportunity_workspaces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table application_history add column scope text not null default 'application'"
    )
    # 0050 oncesi gecmis kayitlari CRM hattindaydi; kesif durumlari yoktu.
    op.execute(
        "update application_history set scope = 'application' "
        "where to_status in ("
        "'preparing', 'applied', 'interview', 'offer', 'accepted', 'rejected', 'withdrawn', 'closed'"
        ")"
    )
    op.execute(
        "update application_history set scope = 'discovery' "
        "where to_status in ('discovered', 'considering', 'trashed')"
    )
    op.execute(
        "create index application_history_scope_idx "
        "on application_history (opportunity_id, scope, at)"
    )
    op.execute(
        "create index opportunity_cluster_key_idx "
        "on opportunity ((raw #>> '{forkjob,cluster_key}')) "
        "where raw ? 'forkjob'"
    )


def downgrade() -> None:
    op.execute("drop index if exists opportunity_cluster_key_idx")
    op.execute("drop index if exists application_history_scope_idx")
    op.execute("alter table application_history drop column if exists scope")
