"""Firsat calisma alanlari: kanonik skor, kesif/basvuru ayrimi, kaynak gozlemi, duyuru alanlari.

Kapsam:
1. `opportunity.score` kanonik kolonu (-1..100). Bugune kadar skor yalnizca
   `raw.forkjob.score` icinde yasiyordu; filtre/siralamada her satirda JSONB
   cast'i yapiliyor ve hicbir index kullanilamiyordu. `raw` aciklama (reasons)
   icin korunur, kolon tek okuma kaynagi olur.
2. Kesif/duyuru yasam dongusu `opportunity.status`'ta kalir; basvuru hatti
   `application.status`'a tasinir. Boylece 19 bin kesfedilmis ilan CRM
   hunisine girmez (AGENTS.md kural 1 ile celismez; entity FK degismez).
3. `opportunity_source_observation`: ilanin kaynak karsisindaki gorunurlugu
   (first/last seen, payload hash, kapanma). Destek tablosu -- PK'si entity.id
   degil, `tests/test_migrations.py` destek listesinde gerekceli istisna.
4. Duyuruya ozel alanlar (resmi kaynak, YLSY parent-child, tarihler, kontenjan).

Idempotent backfill: yalnizca bos/yeni kolonlara dokunur.
"""

from alembic import op

revision = "0050_opportunity_workspaces"
down_revision = "0049_learning_review_backfill"
branch_labels = None
depends_on = None

# Kesif kumesindeki gecerli durumlar (lifecycle.py ile ayni kume).
_DISCOVERY_STATUSES = (
    "discovered",
    "shortlisted",
    "dismissed",
    "archived",
    "closed",
    "new",
    "reviewed",
    "watching",
    "action_required",
    "applied",
    "completed",
    "expired",
)


def upgrade() -> None:
    # ── 1. Kanonik skor ────────────────────────────────────────────────
    op.execute("alter table opportunity add column score double precision")
    op.execute("alter table opportunity add column score_source text")
    op.execute("alter table opportunity add column score_computed_at timestamptz")
    op.execute(
        "alter table opportunity add constraint opportunity_score_range "
        "check (score is null or (score >= -1 and score <= 100))"
    )
    # 0040'taki ifade index'i artik gereksiz: skor JSONB'den cast edilmiyor.
    op.execute("drop index if exists opportunity_score_idx")
    op.execute(
        "create index opportunity_score_idx on opportunity (score desc) "
        "where kind = 'job' and trashed_at is null"
    )

    # ── 2. Kaynak gozlemi / kapanma ────────────────────────────────────
    op.execute("alter table opportunity add column source_status text not null default 'active'")
    op.execute("alter table opportunity add column last_seen_at timestamptz")
    op.execute("alter table opportunity add column missing_since timestamptz")
    op.execute("alter table opportunity add column closed_at timestamptz")
    op.execute(
        "create index opportunity_source_status_idx on opportunity (source_status) "
        "where source_status <> 'active'"
    )

    # ── 3. Duyuruya ozel alanlar ───────────────────────────────────────
    op.execute("alter table opportunity add column official boolean")
    op.execute(
        "alter table opportunity add column parent_id uuid "
        "references opportunity(id) on delete set null"
    )
    op.execute("alter table opportunity add column stage text")
    op.execute("alter table opportunity add column application_start_at timestamptz")
    op.execute("alter table opportunity add column application_end_at timestamptz")
    op.execute("alter table opportunity add column exam_at timestamptz")
    op.execute("alter table opportunity add column result_at timestamptz")
    op.execute("alter table opportunity add column guide_url text")
    op.execute("alter table opportunity add column apply_url text")
    op.execute("alter table opportunity add column quota_total integer")
    op.execute("alter table opportunity add column fields jsonb not null default '[]'::jsonb")
    op.execute(
        "create index opportunity_parent_idx on opportunity (parent_id) where parent_id is not null"
    )

    # ── 4. Basvuru hatti ───────────────────────────────────────────────
    op.execute("alter table application add column status text")
    op.execute("alter table application add column status_changed_at timestamptz")

    # ── 5. Kaynak gozlem tablosu (destek tablosu) ──────────────────────
    op.execute(
        """create table opportunity_source_observation (
          id uuid primary key default gen_random_uuid(),
          opportunity_id uuid not null references opportunity(id) on delete cascade,
          source text not null,
          external_id text,
          canonical_url text,
          payload_hash text,
          source_status text not null default 'active',
          first_seen_at timestamptz not null default now(),
          last_seen_at timestamptz not null default now(),
          last_successful_seen_at timestamptz,
          source_published_at timestamptz,
          source_removed_at timestamptz,
          constraint opportunity_source_observation_uniq unique (opportunity_id, source)
        )"""
    )
    op.execute(
        "create index opportunity_source_observation_source_idx "
        "on opportunity_source_observation (source, external_id)"
    )

    # ── 6. Backfill: kanonik skor ──────────────────────────────────────
    op.execute(
        """
        update opportunity
           set score = (raw -> 'forkjob' ->> 'score')::double precision,
               score_source = 'forkjob-rules',
               score_computed_at = now()
         where score is null
           and jsonb_typeof(raw -> 'forkjob' -> 'score') = 'number'
        """
    )
    op.execute(
        "update opportunity set score_source = 'forkjob-rules' "
        "where score is not null and score_source is null"
    )

    # ── 7. Backfill: kaynak gozlemi (mevcut ilk/son gorulme) ───────────
    op.execute(
        """
        insert into opportunity_source_observation (
            opportunity_id, source, external_id, canonical_url, payload_hash,
            source_status, first_seen_at, last_seen_at, last_successful_seen_at,
            source_published_at
        )
        select o.id,
               o.source,
               o.external_id,
               o.url,
               null,
               'active',
               coalesce(fs.seen, o.found_at),
               coalesce(ls.seen, o.found_at),
               coalesce(ls.seen, o.found_at),
               o.published_at
          from opportunity o
          cross join lateral (
            select case
                     when o.raw -> 'forkjob' ->> 'first_seen' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
                     then (o.raw -> 'forkjob' ->> 'first_seen')::timestamptz
                   end as seen
          ) fs
          cross join lateral (
            select case
                     when o.raw -> 'forkjob' ->> 'last_seen' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
                     then (o.raw -> 'forkjob' ->> 'last_seen')::timestamptz
                   end as seen
          ) ls
         where o.trashed_at is null
           and not exists (
             select 1 from opportunity_source_observation obs
              where obs.opportunity_id = o.id and obs.source = o.source
           )
        """
    )
    op.execute(
        "update opportunity set last_seen_at = o.last_seen "
        "from (select opportunity_id, max(last_seen_at) as last_seen "
        "from opportunity_source_observation group by opportunity_id) o "
        "where opportunity.id = o.opportunity_id and opportunity.last_seen_at is null"
    )

    # ── 8. Backfill: application.status ────────────────────────────────
    op.execute(
        """
        update application a
           set status = case
                 when o.status = 'preparing' then 'preparing'
                 when o.status = 'interview' then 'interview'
                 when o.status = 'offer' then 'offer'
                 when o.status = 'accepted' then 'accepted'
                 when o.status = 'rejected' then 'rejected'
                 when o.status = 'withdrawn' then 'withdrawn'
                 when o.status = 'closed' then 'closed'
                 else 'applied'
               end,
               status_changed_at = coalesce(a.created_at, now())
          from opportunity o
         where a.opportunity_id = o.id
           and a.status is null
        """
    )
    # Basvuru yapildigi halde CRM satiri olmayan eski kayitlar kaybolmasin.
    op.execute(
        """
        insert into application (opportunity_id, posting_snapshot, status, status_changed_at)
        select o.id,
               '{}'::jsonb,
               case
                 when o.status = 'preparing' then 'preparing'
                 when o.status = 'interview' then 'interview'
                 when o.status = 'offer' then 'offer'
                 when o.status = 'accepted' then 'accepted'
                 when o.status = 'rejected' then 'rejected'
                 when o.status = 'withdrawn' then 'withdrawn'
                 when o.status = 'closed' then 'closed'
                 else 'applied'
               end,
               coalesce(o.applied_at, now())
          from opportunity o
         where o.kind = 'job'
           and o.status in (
             'preparing', 'applied', 'interview', 'offer',
             'accepted', 'rejected', 'withdrawn', 'closed'
           )
           and not exists (select 1 from application a where a.opportunity_id = o.id)
        """
    )
    op.execute("alter table application alter column status set default 'applied'")
    op.execute("alter table application alter column status set not null")

    # ── 9. Backfill: durum kumelerini ayir ─────────────────────────────
    op.execute("update opportunity set trashed_at = now() where status = 'trashed'")
    op.execute(
        "update opportunity set trashed_from_status = 'discovered' "
        "where status = 'trashed' and trashed_from_status is null"
    )
    op.execute(
        "update opportunity set trashed_from_status = 'discovered' "
        "where trashed_from_status is not null and trashed_from_status not in "
        "('discovered', 'shortlisted', 'dismissed', 'archived', 'closed')"
    )
    # Is ilanlari: kesif dongusu
    op.execute(
        """
        update opportunity
           set status = case
                 when status in ('considering', 'preparing', 'applied', 'interview', 'offer')
                   then 'shortlisted'
                 when status in ('accepted', 'rejected', 'withdrawn', 'closed')
                   then 'archived'
                 when status = 'trashed' then 'dismissed'
                 else 'discovered'
               end
         where kind = 'job'
           and status in (
             'considering', 'preparing', 'applied', 'interview', 'offer',
             'accepted', 'rejected', 'withdrawn', 'closed', 'trashed'
           )
        """
    )
    # Duyurular: duyuru dongusu
    op.execute(
        """
        update opportunity
           set status = case
                 when status = 'discovered' then 'new'
                 when status in ('considering', 'preparing') then 'reviewed'
                 when status = 'applied' then 'applied'
                 when status in ('accepted', 'rejected', 'withdrawn', 'closed') then 'archived'
                 when status = 'trashed' then 'dismissed'
                 else status
               end
         where kind <> 'job'
           and status in (
             'discovered', 'considering', 'preparing', 'applied',
             'accepted', 'rejected', 'withdrawn', 'closed', 'trashed'
           )
        """
    )


def downgrade() -> None:
    # Durum kumelerini eski CRM akisina geri esle (mumkun oldugu kadar).
    op.execute(
        "update opportunity set status = 'considering' "
        "where kind = 'job' and status in ('shortlisted', 'dismissed')"
    )
    op.execute(
        "update opportunity set status = 'discovered' "
        "where kind = 'job' and status in ('discovered', 'archived', 'closed')"
    )
    op.execute("update opportunity set status = 'discovered' where kind <> 'job'")

    op.execute("drop index if exists opportunity_source_observation_source_idx")
    op.execute("drop table if exists opportunity_source_observation")
    op.execute("alter table application alter column status drop not null")
    op.execute("alter table application alter column status drop default")
    op.execute("alter table application drop column if exists status_changed_at")
    op.execute("alter table application drop column if exists status")
    op.execute("drop index if exists opportunity_parent_idx")
    op.execute("alter table opportunity drop column if exists fields")
    op.execute("alter table opportunity drop column if exists quota_total")
    op.execute("alter table opportunity drop column if exists apply_url")
    op.execute("alter table opportunity drop column if exists guide_url")
    op.execute("alter table opportunity drop column if exists result_at")
    op.execute("alter table opportunity drop column if exists exam_at")
    op.execute("alter table opportunity drop column if exists application_end_at")
    op.execute("alter table opportunity drop column if exists application_start_at")
    op.execute("alter table opportunity drop column if exists stage")
    op.execute("alter table opportunity drop column if exists parent_id")
    op.execute("alter table opportunity drop column if exists official")
    op.execute("drop index if exists opportunity_source_status_idx")
    op.execute("alter table opportunity drop column if exists closed_at")
    op.execute("alter table opportunity drop column if exists missing_since")
    op.execute("alter table opportunity drop column if exists last_seen_at")
    op.execute("alter table opportunity drop column if exists source_status")
    op.execute("drop index if exists opportunity_score_idx")
    op.execute(
        "create index opportunity_score_idx on opportunity "
        "((cast(raw->'forkjob'->>'score' as float)) desc nulls last)"
    )
    op.execute("alter table opportunity drop constraint if exists opportunity_score_range")
    op.execute("alter table opportunity drop column if exists score_computed_at")
    op.execute("alter table opportunity drop column if exists score_source")
    op.execute("alter table opportunity drop column if exists score")
