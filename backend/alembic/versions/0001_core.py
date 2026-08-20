"""cekirdek: entity, link, event, tag, saved_view, source_run

Revision ID: 0001_core
Revises:
"""
from alembic import op

revision = "0001_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    create extension if not exists pgcrypto;
    create extension if not exists pg_trgm;
    create extension if not exists unaccent;

    -- unaccent() IMMUTABLE degil, generated column'da dogrudan kullanilamaz.
    -- Bu wrapper olmadan entity tablosu olusmaz.
    create or replace function immutable_unaccent(text)
      returns text
      language sql immutable strict parallel safe as
    $$ select public.unaccent('public.unaccent'::regdictionary, $1) $$;

    create table entity (
      id           uuid primary key default gen_random_uuid(),
      type         text        not null,
      title        text        not null default '',
      search_text  text        not null default '',
      created_at   timestamptz not null default now(),
      updated_at   timestamptz not null default now(),
      archived_at  timestamptz,
      search_vec   tsvector generated always as (
                     to_tsvector('simple', immutable_unaccent(title || ' ' || search_text))
                   ) stored
    );
    create index entity_type_idx    on entity (type) where archived_at is null;
    create index entity_search_idx  on entity using gin (search_vec);
    create index entity_trgm_idx    on entity using gin (title gin_trgm_ops);
    create index entity_updated_idx on entity (updated_at desc);

    create table link (
      id         uuid primary key default gen_random_uuid(),
      from_id    uuid not null references entity(id) on delete cascade,
      to_id      uuid not null references entity(id) on delete cascade,
      relation   text not null default 'related',
      created_at timestamptz not null default now(),
      constraint link_no_self check (from_id <> to_id),
      constraint link_uniq unique (from_id, to_id, relation)
    );
    create index link_to_idx on link (to_id);

    create table event (
      id          bigserial primary key,
      entity_id   uuid references entity(id) on delete set null,
      entity_type text,
      verb        text        not null,
      payload     jsonb       not null default '{}',
      occurred_at timestamptz not null default now()
    );
    create index event_time_idx on event (occurred_at desc);
    create index event_verb_idx on event (verb, occurred_at desc);

    create table tag (
      id    uuid primary key default gen_random_uuid(),
      name  text not null,
      color text
    );
    create unique index tag_name_uniq on tag (lower(name));

    create table entity_tag (
      entity_id uuid references entity(id) on delete cascade,
      tag_id    uuid references tag(id)    on delete cascade,
      primary key (entity_id, tag_id)
    );

    create table saved_view (
      id       uuid primary key default gen_random_uuid(),
      name     text    not null,
      module   text    not null,
      filter   jsonb   not null default '{}',
      sort     text,
      pinned   boolean not null default false,
      position int     not null default 0
    );

    create table source_run (
      id          bigserial primary key,
      source      text not null,
      started_at  timestamptz not null default now(),
      finished_at timestamptz,
      status      text not null default 'ok',
      items_found int  not null default 0,
      error       text
    );
    create index source_run_idx on source_run (source, started_at desc);
    """)


def downgrade() -> None:
    op.execute("""
    drop table if exists source_run, saved_view, entity_tag, tag, event, link, entity cascade;
    drop function if exists immutable_unaccent(text);
    """)
