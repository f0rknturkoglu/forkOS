"""Media tracker domain tables and shared notification ownership."""

from alembic import op

revision = "0026_media_domain"
down_revision = "0025_document_folder_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table media_item alter column progress type numeric(12,2) "
        "using progress::numeric(12,2)"
    )
    op.execute(
        "alter table media_item alter column total type numeric(12,2) "
        "using total::numeric(12,2)"
    )
    op.execute("alter table media_item add column summary text")
    op.execute("alter table media_item add column release_date date")
    op.execute("alter table media_item add column progress_measure text")
    op.execute("alter table media_item add column review text")
    op.execute("alter table media_item add column favorite boolean not null default false")
    op.execute("alter table media_item add column owned boolean not null default false")
    op.execute(
        "alter table media_item add column ownership jsonb not null default '{}'::jsonb"
    )
    op.execute("alter table media_item add column monitored boolean not null default false")
    op.execute("alter table media_item add column provider text")
    op.execute("alter table media_item add column provider_id text")
    op.execute(
        "alter table media_item add column provider_ids jsonb not null default '{}'::jsonb"
    )
    op.execute("alter table media_item add column cover_url text")
    op.execute("alter table media_item add column cover_path text")
    op.execute("alter table media_item add column backdrop_url text")
    op.execute("alter table media_item add column backdrop_path text")
    op.execute("alter table media_item add column last_synced_at timestamptz")
    op.execute(
        "alter table media_item add constraint media_item_kind_check "
"check (kind in ('movie','show','anime','manga','book','audiobook',"
        "'podcast','music','game'))"
    )
    op.execute(
        "alter table media_item add constraint media_item_status_check "
        "check (status in ('planned','in_progress','paused','completed','dropped'))"
    )
    op.execute(
        "alter table media_item add constraint media_item_progress_measure_check "
        "check (progress_measure is null or progress_measure in "
        "('item','episode','chapter','page','minute','hour','track'))"
    )
    op.execute(
        "create unique index media_item_provider_ref_uniq "
        "on media_item (provider,provider_id) "
        "where provider is not null and provider_id is not null"
    )

    op.execute(
        """create table media_unit (
          id uuid primary key references entity(id) on delete cascade,
          media_id uuid not null references media_item(id) on delete restrict,
          parent_id uuid references media_unit(id) on delete set null,
          unit_type text not null,
          number numeric(10,3),
          duration_min int,
          release_at timestamptz,
          progress_total numeric(12,2),
          progress_measure text,
          provider text,
          provider_id text,
          provider_ids jsonb not null default '{}'::jsonb,
          cover_url text,
          cover_path text,
          meta jsonb not null default '{}'::jsonb,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint media_unit_type_check check (
            unit_type in ('season','episode','volume','chapter','album','track','podcast_episode')
          ),
          constraint media_unit_progress_measure_check check (
            progress_measure is null or progress_measure in
              ('item','episode','chapter','page','minute','hour','track')
          )
        )"""
    )
    op.execute("create index media_unit_media_idx on media_unit (media_id, unit_type, number)")
    op.execute(
        "create unique index media_unit_provider_ref_uniq "
        "on media_unit (media_id,provider,provider_id) "
        "where provider is not null and provider_id is not null"
    )

    op.execute(
        """create table media_cycle (
          id uuid primary key references entity(id) on delete cascade,
          media_id uuid not null references media_item(id) on delete restrict,
          ordinal int not null,
          status text not null default 'active',
          started_at timestamptz not null,
          completed_at timestamptz,
          last_caught_up_at timestamptz,
          score smallint,
          notes text,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint media_cycle_media_ordinal_uniq unique (media_id,ordinal),
          constraint media_cycle_status_check check (
            status in ('active','paused','completed','dropped')
          )
        )"""
    )
    op.execute(
        "create unique index media_cycle_one_open_idx on media_cycle (media_id) "
        "where completed_at is null and status in ('active','paused')"
    )

    op.execute(
        """create table media_consumption (
          id uuid primary key references entity(id) on delete cascade,
          media_id uuid not null references media_item(id) on delete restrict,
          cycle_id uuid not null references media_cycle(id) on delete restrict,
          unit_id uuid references media_unit(id) on delete set null,
          client_uuid uuid not null,
          action text not null,
          measure text,
          amount numeric(12,2),
          progress_after numeric(12,2),
          occurred_at timestamptz not null default now(),
          duration_min int,
          note text,
          meta jsonb not null default '{}'::jsonb,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint media_consumption_client_uuid_uniq unique (client_uuid),
          constraint media_consumption_action_check check (
            action in ('quick','set','complete_unit','uncomplete_unit','finish')
          ),
          constraint media_consumption_measure_check check (
            measure is null or measure in
              ('item','episode','chapter','page','minute','hour','track')
          )
        )"""
    )
    op.execute(
        "create index media_consumption_media_time_idx "
        "on media_consumption (media_id, occurred_at desc)"
    )
    op.execute(
        "create index media_consumption_cycle_time_idx "
        "on media_consumption (cycle_id, occurred_at desc)"
    )

    op.execute(
        """create table media_collection (
          id uuid primary key references entity(id) on delete cascade,
          description text,
          color varchar(16),
          position int not null default 0,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )"""
    )
    op.execute(
        "create index media_collection_item_link_idx on link (from_id,to_id) "
        "where relation = 'media.collection_item'"
    )

    op.execute("alter table source_sync_batch add column scope text")
    op.execute(
        "update source_sync_batch set scope = 'opportunity' where scope is null"
    )
    op.execute(
        "alter table source_sync_batch alter column scope set default 'opportunity'"
    )
    op.execute("alter table source_sync_batch alter column scope set not null")
    op.execute(
        "create index source_sync_batch_scope_time_idx "
        "on source_sync_batch (scope, created_at desc)"
    )


def downgrade() -> None:
    op.execute("drop index if exists source_sync_batch_scope_time_idx")
    op.execute("alter table source_sync_batch drop column if exists scope")
    op.execute("delete from entity where type = 'media_consumption'")
    op.execute("delete from entity where type = 'media_cycle'")
    op.execute("delete from entity where type = 'media_unit'")
    op.execute("delete from entity where type = 'media_collection'")
    op.execute("drop index if exists media_collection_item_link_idx")
    op.execute("drop table if exists media_collection")
    op.execute("drop index if exists media_consumption_cycle_time_idx")
    op.execute("drop index if exists media_consumption_media_time_idx")
    op.execute("drop table if exists media_consumption")
    op.execute("drop index if exists media_cycle_one_open_idx")
    op.execute("drop table if exists media_cycle")
    op.execute("drop index if exists media_unit_provider_ref_uniq")
    op.execute("drop index if exists media_unit_media_idx")
    op.execute("drop table if exists media_unit")
    op.execute("drop index if exists media_item_provider_ref_uniq")
    op.execute(
        "alter table media_item drop constraint if exists media_item_progress_measure_check"
    )
    op.execute("alter table media_item drop constraint if exists media_item_status_check")
    op.execute("alter table media_item drop constraint if exists media_item_kind_check")
    op.execute("alter table media_item drop column if exists last_synced_at")
    op.execute("alter table media_item drop column if exists backdrop_path")
    op.execute("alter table media_item drop column if exists backdrop_url")
    op.execute("alter table media_item drop column if exists cover_path")
    op.execute("alter table media_item drop column if exists cover_url")
    op.execute("alter table media_item drop column if exists provider_ids")
    op.execute("alter table media_item drop column if exists provider_id")
    op.execute("alter table media_item drop column if exists provider")
    op.execute("alter table media_item drop column if exists monitored")
    op.execute("alter table media_item drop column if exists ownership")
    op.execute("alter table media_item drop column if exists owned")
    op.execute("alter table media_item drop column if exists favorite")
    op.execute("alter table media_item drop column if exists review")
    op.execute("alter table media_item drop column if exists progress_measure")
    op.execute("alter table media_item drop column if exists release_date")
    op.execute("alter table media_item drop column if exists summary")
    op.execute(
        "alter table media_item alter column total type integer "
        "using round(total)::integer"
    )
    op.execute(
        "alter table media_item alter column progress type integer "
        "using round(progress)::integer"
    )
