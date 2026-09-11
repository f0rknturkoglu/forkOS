"""Ogrenme calisma alani: SRS alanlari, kaynak kaynagi ve DB kisitlari.

Faz 1: `study_topic`e mastery/SRS kolonlari, `learning_resource`a yer imi/kurs
bagi + source + sure tahmini; ikisine de CHECK kisitlari ve stale/tekrar
sorgularini besleyen index'ler eklenir. Veri SILINMEZ: `source` varsayilani
'manual' oldugu icin mevcut kaynaklar korunur.
"""

from alembic import op

revision = "0048_learning_workspace"
down_revision = "0047_media_session_action"
branch_labels = None
depends_on = None

_STATUSES = "'not_started','in_progress','done'"
_KINDS = "'link','video','article','course','book','doc','exercise'"
_SOURCES = "'manual','bookmark','import'"
_COURSE_STATUSES = "'planned','in_progress','done','dropped'"


def upgrade() -> None:
    # ── study_topic: mastery + SRS ──────────────────────────────────────
    op.execute("alter table study_topic add column mastery smallint")
    op.execute("alter table study_topic add column interval_days integer not null default 0")
    op.execute("alter table study_topic add column ease double precision not null default 2.5")
    op.execute("alter table study_topic add column review_count integer not null default 0")
    op.execute("alter table study_topic add column last_reviewed_at timestamptz")
    op.execute("alter table study_topic add column next_review_at timestamptz")
    op.execute(
        f"alter table study_topic add constraint study_topic_status_check "
        f"check (status in ({_STATUSES}))"
    )
    op.execute(
        "alter table study_topic add constraint study_topic_confidence_check "
        "check (confidence is null or (confidence >= 1 and confidence <= 5))"
    )
    op.execute(
        "alter table study_topic add constraint study_topic_target_min_check "
        "check (target_min is null or target_min >= 1)"
    )
    op.execute(
        "alter table study_topic add constraint study_topic_mastery_check "
        "check (mastery is null or (mastery >= 0 and mastery <= 100))"
    )
    op.execute(
        "alter table study_topic add constraint study_topic_parent_not_self "
        "check (parent_id is null or parent_id <> id)"
    )

    # ── course: durum/progress tutarliligi ──────────────────────────────
    op.execute(
        f"alter table course add constraint course_status_check "
        f"check (status in ({_COURSE_STATUSES}))"
    )
    op.execute(
        "alter table course add constraint course_progress_pct_check "
        "check (progress_pct >= 0 and progress_pct <= 100)"
    )

    # ── learning_resource: yer imi/kurs bagi + source + tahmin ──────────
    op.execute(
        "alter table learning_resource add column bookmark_id uuid "
        "references bookmark(id) on delete set null"
    )
    op.execute(
        "alter table learning_resource add column course_id uuid "
        "references course(id) on delete set null"
    )
    op.execute(
        "alter table learning_resource add column source text not null default 'manual'"
    )
    op.execute("alter table learning_resource add column estimated_min integer")
    op.execute("alter table learning_resource add column last_opened_at timestamptz")
    op.execute(
        f"alter table learning_resource add constraint learning_resource_kind_check "
        f"check (kind in ({_KINDS}))"
    )
    op.execute(
        f"alter table learning_resource add constraint learning_resource_source_check "
        f"check (source in ({_SOURCES}))"
    )
    op.execute(
        "alter table learning_resource add constraint learning_resource_estimated_min_check "
        "check (estimated_min is null or estimated_min >= 1)"
    )
    op.execute(
        "create unique index learning_resource_bookmark_uniq "
        "on learning_resource (topic_id, bookmark_id) where bookmark_id is not null"
    )

    # ── Sorgu index'leri: tekrar kuyrugu ve stale listesi ───────────────
    op.execute(
        "create index study_topic_next_review_idx on study_topic (next_review_at) "
        "where next_review_at is not null"
    )
    op.execute("create index study_topic_last_studied_idx on study_topic (last_studied_at)")


def downgrade() -> None:
    op.execute("drop index if exists study_topic_last_studied_idx")
    op.execute("drop index if exists study_topic_next_review_idx")
    op.execute("drop index if exists learning_resource_bookmark_uniq")
    op.execute(
        "alter table learning_resource drop constraint if exists learning_resource_estimated_min_check"
    )
    op.execute(
        "alter table learning_resource drop constraint if exists learning_resource_source_check"
    )
    op.execute("alter table learning_resource drop constraint if exists learning_resource_kind_check")
    op.execute("alter table learning_resource drop column if exists last_opened_at")
    op.execute("alter table learning_resource drop column if exists estimated_min")
    op.execute("alter table learning_resource drop column if exists source")
    op.execute("alter table learning_resource drop column if exists course_id")
    op.execute("alter table learning_resource drop column if exists bookmark_id")
    op.execute("alter table course drop constraint if exists course_progress_pct_check")
    op.execute("alter table course drop constraint if exists course_status_check")
    op.execute("alter table study_topic drop constraint if exists study_topic_parent_not_self")
    op.execute("alter table study_topic drop constraint if exists study_topic_mastery_check")
    op.execute("alter table study_topic drop constraint if exists study_topic_target_min_check")
    op.execute("alter table study_topic drop constraint if exists study_topic_confidence_check")
    op.execute("alter table study_topic drop constraint if exists study_topic_status_check")
    op.execute("alter table study_topic drop column if exists next_review_at")
    op.execute("alter table study_topic drop column if exists last_reviewed_at")
    op.execute("alter table study_topic drop column if exists review_count")
    op.execute("alter table study_topic drop column if exists ease")
    op.execute("alter table study_topic drop column if exists interval_days")
    op.execute("alter table study_topic drop column if exists mastery")
