"""Remove habit module (K1): habits live on as recurring todos.

habit.habit_log tablosunda veri varsa aktif aliskanliklar once `todo` + `recur`
olarak tasinir; tablolar sonra dusurulur.
"""

from alembic import op

revision = "0024_remove_habit"
down_revision = "0023_application_crm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Aktif aliskanligin entity kaydini todo'ya cevir (baslik entity'de durur).
    op.execute("update entity set type = 'todo' where id in (select id from habit where active)")
    # 2) Todo kaydini olustur; rutin kadansi todo.recur'a tasinir.
    op.execute(
        """insert into todo (id, description, priority, status, due_at, reminder_at,
                             completed_at, parent_id, position, recur,
                             recur_origin_id, milestone_id)
           select h.id, null, 2, 'open', null, null, null, null, h.position,
                  case when h.cadence = 'weekly' then 'weekly' else 'daily' end,
                  null, null
           from habit h
           where h.active"""
    )
    # 3) Pasif aliskanliklarin entity kayitlarini temizle (habit_log cascade'le duser).
    op.execute("delete from entity where id in (select id from habit where not active)")
    # 4) Tablolari kaldir.
    op.execute("drop table if exists habit_log")
    op.execute("drop table if exists habit")


def downgrade() -> None:
    # Geri donuste hangi todo'nun eski aliskanlik oldugu ayirt edilemez;
    # tablolar bos olarak geri gelir (K1 veriyi todo'ya tasidigi icin kayip yok).
    op.execute(
        """create table habit (
          id              uuid primary key references entity(id) on delete cascade,
          cadence         text    not null default 'daily',
          target_per_week int     not null default 7,
          color           text,
          active          boolean not null default true,
          position        int     not null default 0
        )"""
    )
    op.execute(
        """create table habit_log (
          habit_id uuid not null references habit(id) on delete cascade,
          day      date not null,
          done     boolean not null default true,
          note     text,
          primary key (habit_id, day)
        )"""
    )
