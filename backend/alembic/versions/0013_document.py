"""Drive document metadata and OAuth tokens."""

from alembic import op

revision = "0013_document"
down_revision = "0012_course_book"
branch_labels = None
depends_on = None

UPGRADE = [
    """create table document (
      id uuid primary key references entity(id) on delete cascade,
      drive_file_id text not null unique,
      mime text,
      category text,
      web_view_link text,
      size_bytes bigint,
      drive_modified_at timestamptz,
      synced_at timestamptz not null default now()
    )""",
    "create index document_category_idx on document (category)",
    """create table oauth_token (
      provider text primary key,
      access_token text not null,
      refresh_token text,
      expires_at timestamptz,
      scopes text,
      sync_token text
    )""",
]


def upgrade():
    for statement in UPGRADE:
        op.execute(statement)


def downgrade():
    op.execute("drop table if exists oauth_token cascade")
    op.execute("drop table if exists document cascade")
