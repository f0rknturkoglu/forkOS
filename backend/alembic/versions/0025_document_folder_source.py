"""Drive belge klasörü kaynağını koru."""

from alembic import op

revision = "0025_document_folder_source"
down_revision = "0024_todo_milestone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Kural 10: her komut ayrı op.execute.
    op.execute("alter table document add column folder_id text")
    op.execute(
        "create index document_folder_category_idx on document (folder_id, category)"
    )


def downgrade() -> None:
    op.execute("drop index if exists document_folder_category_idx")
    op.execute("alter table document drop column if exists folder_id")
