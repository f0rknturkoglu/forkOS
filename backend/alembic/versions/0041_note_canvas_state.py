"""Notlara Excalidraw tuvali ve gorunum tercihleri ekle (kural 10)."""

from alembic import op

revision = "0041_note_canvas_state"
down_revision = "0040_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table note add column canvas_state jsonb not null default '{}'::jsonb")
    op.execute("alter table note add column default_view text not null default 'page'")
    op.execute("alter table note add column page_width text not null default 'compact'")
    op.execute(
        "alter table note add constraint note_default_view_ck "
        "check (default_view in ('page', 'canvas'))"
    )
    op.execute(
        "alter table note add constraint note_page_width_ck "
        "check (page_width in ('compact', 'wide', 'full'))"
    )


def downgrade() -> None:
    op.execute("alter table note drop constraint note_page_width_ck")
    op.execute("alter table note drop constraint note_default_view_ck")
    op.execute("alter table note drop column page_width")
    op.execute("alter table note drop column default_view")
    op.execute("alter table note drop column canvas_state")
