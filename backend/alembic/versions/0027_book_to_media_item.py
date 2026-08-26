"""Merge learning.book into media_item (Faz 11).

Karar dokumani: docs/faz11-kitap-esleme.md. media_item kazanir; book satirlari
entity.id KORUNARAK media_item'a tasinir (link/event/tag/bookmark baglari
kirilmaz), entity.type guncellenir, book tablosu duser. Tasinan kayitlara
meta.legacy_book isareti konur -- downgrade hangi kayitlarin geri donecegini
bilsin (sonradan medyada eklenen kind='book' kayitlari karismasin).

Her SQL komutu ayri op.execute() (kural 10 -- asyncpg tek prepared statement).
"""

from alembic import op

revision = "0027_book_to_media_item"
down_revision = "0025_drop_deadline_v"
branch_labels = None
depends_on = None

#: book.status (serbest metin) -> media_item STATUSES (check constraint).
_STATUS_MAP = """
case b.status
  when 'want' then 'planned'
  when 'reading' then 'in_progress'
  when 'done' then 'completed'
  when 'finished' then 'completed'
  when 'paused' then 'paused'
  when 'dropped' then 'dropped'
  else 'planned'
end
"""

#: Ters yon -- downgrade icin.
_REVERSE_STATUS_MAP = """
case m.status
  when 'planned' then 'want'
  when 'in_progress' then 'reading'
  when 'completed' then 'done'
  when 'paused' then 'paused'
  when 'dropped' then 'dropped'
  else 'want'
end
"""


def upgrade() -> None:
    # 1) Book satirlarini media_item'a tasi; id KORUNUR. progress_measure='page',
    #    yazar meta.author'a, rating score'a, eski kitap isareti meta'ya.
    op.execute(
        f"""
        insert into media_item (id, kind, status, progress, total, score, notes,
                                started_at, finished_at, meta, progress_measure)
        select b.id, 'book', {_STATUS_MAP}, b.current_page, b.total_pages, b.rating,
               b.notes,
               (b.started_at::timestamp at time zone 'UTC'),
               (b.finished_at::timestamp at time zone 'UTC'),
               jsonb_strip_nulls(jsonb_build_object('author', b.author,
                                                    'legacy_book', to_jsonb(true))),
               'page'
        from book b
        """
    )
    # 2) Tasinan kitaplarin entity tipini media_item yap.
    op.execute(
        "update entity set type = 'media_item' where type = 'book' "
        "and id in (select id from media_item where meta ->> 'legacy_book' = 'true')"
    )
    # 3) Kitap tablosu emekli.
    op.execute("drop table book")


def downgrade() -> None:
    # 1) Eski book semasini geri getir (upgrade'de dusuruldu).
    op.execute(
        """
        create table book (
            id uuid not null primary key references entity (id) on delete cascade,
            author text,
            status text not null,
            total_pages integer,
            current_page integer not null,
            started_at date,
            finished_at date,
            rating smallint,
            notes text
        )
        """
    )
    # 2) Yalniz migration ile tasinanlari geri tasi (legacy_book isareti).
    op.execute(
        f"""
        insert into book (id, author, status, total_pages, current_page,
                          started_at, finished_at, rating, notes)
        select m.id, m.meta ->> 'author', {_REVERSE_STATUS_MAP},
               m.total, m.progress,
               (m.started_at::timestamp at time zone 'UTC')::date,
               (m.finished_at::timestamp at time zone 'UTC')::date,
               m.score, m.notes
        from media_item m
        where m.kind = 'book' and m.meta ->> 'legacy_book' = 'true'
        """
    )
    # 3) Entity tipleri geri al.
    op.execute(
        "update entity set type = 'book' where id in (select id from book)"
    )
    # 4) Tasinan media_item kayitlarini sil (book satiri artik sahibi).
    op.execute(
        "delete from media_item where kind = 'book' and meta ->> 'legacy_book' = 'true'"
    )
