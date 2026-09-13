"""source_run: taranan kapsam + kosum durumu kisiti (complete/partial/empty/error).

`items_found` "kac yeni firsat eklendi" demekti; kaynagin kac kayit gordugunu
tutacak ayri bir alan yoktu. Kapsam karsilastirmasi (onceki tam kosu 100 kayit
gordu, bu kosu 12 gordu -> sayfalama bozulmus) bu alan olmadan yapilamaz ve
eksik taranan bir kosu "12 ilan kapandi" diye yanlis kapanma taramasini
tetikler.

`status` icin de artik bir kisit var: `ok` (complete) | `partial` | `empty` |
`error` | `running` | `abandoned` | `disabled`. Yeni `partial` durumu "kaynak
calisiyor ama hedefledigi kapsamin tamamini taramadi" demektir; kapanma
taramasi yalniz `ok` kosumda yapilir.
"""

from alembic import op

revision = "0054_source_run_scope"
down_revision = "0053_bookmark_pocket_engine"
branch_labels = None
depends_on = None

#: source_run.status icin gecerli kume. `disabled` eski surumlerin kapattigi
#: kaynaklar icin korunur (mevcut satirlarda gorulur), `partial` bu surumle gelir.
_STATUSES = ("running", "ok", "partial", "empty", "error", "abandoned", "disabled")


def upgrade() -> None:
    op.execute("alter table source_run add column items_seen integer not null default 0")
    # Gecmis satirlarda taranan kapsam kaydedilmemisti; en yakin tahmin
    # eklenen kayit sayisidir (kapsam korumasi tabani ilk kosuda muhafazakar kalsin).
    op.execute("update source_run set items_seen = items_found")
    op.execute(
        "alter table source_run add constraint source_run_status_check "
        "check (status in (" + ", ".join(f"'{value}'" for value in _STATUSES) + "))"
    )
    # Batch ozetinde `partial` ayri sayilir; sayilmazsa partial iceren bir batch
    # hicbir zaman tamamlanmis sayilmaz.
    op.execute(
        "alter table source_sync_batch add column partial_sources integer not null default 0"
    )


def downgrade() -> None:
    op.execute("alter table source_sync_batch drop column if exists partial_sources")
    op.execute("alter table source_run drop constraint if exists source_run_status_check")
    op.execute("alter table source_run drop column if exists items_seen")
