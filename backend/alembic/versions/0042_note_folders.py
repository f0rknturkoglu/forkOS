"""Not klasorleri ve not -> klasor bagi (kural 10)."""

from alembic import op

revision = "0042_note_folders"
down_revision = "0041_note_canvas_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """create table note_folder (
            id uuid primary key references entity(id) on delete cascade,
            parent_id uuid null references note_folder(id) on delete set null,
            position integer not null default 0,
            constraint note_folder_no_self_ck check (parent_id is null or parent_id <> id)
        )"""
    )
    op.execute("create index note_folder_parent_position_idx on note_folder(parent_id, position)")
    op.execute("alter table note add column folder_id uuid null")
    op.execute(
        "alter table note add constraint note_folder_fk "
        "foreign key (folder_id) references note_folder(id) on delete set null"
    )
    op.execute("create index note_folder_id_idx on note(folder_id)")


def downgrade() -> None:
    op.execute("drop index note_folder_id_idx")
    op.execute("alter table note drop constraint note_folder_fk")
    op.execute("alter table note drop column folder_id")
    op.execute("drop index note_folder_parent_position_idx")
    op.execute("drop table note_folder")
