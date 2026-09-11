"""source_run hata sinifi.

Arayuz TLS/DNS/timeout/HTTP/parser hatalarini ayni kefeye koymamali; kapanma
tespiti ve devre kesici de bu sinifa gore karar verir. `error` metni
sanitize edilmis insan-okur mesaj olarak kalir.
"""

from alembic import op

revision = "0052_source_run_error_kind"
down_revision = "0051_opportunity_history_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table source_run add column error_kind varchar(24)")
    # Gecmis hatalar siniflandirilamaz; yalnizca "unknown" olarak isaretlenir.
    op.execute("update source_run set error_kind = 'unknown' where error is not null")


def downgrade() -> None:
    op.execute("alter table source_run drop column if exists error_kind")
