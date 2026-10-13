"""Additive Living Goals graph. Downgrade retains accepted graph history."""
import sqlalchemy as sa
from alembic import op

revision = "0081_goal_roadmap"
down_revision = "0080_goal_studio_capture"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("goal_roadmap_node"):
        op.execute("""CREATE TABLE goal_roadmap_node (
            id UUID PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
            goal_id UUID NOT NULL REFERENCES goal(id),
            parent_id UUID REFERENCES goal_roadmap_node(id),
            target_id UUID REFERENCES entity(id) ON DELETE SET NULL,
            kind VARCHAR(20) NOT NULL CHECK (kind IN ('period','phase','milestone','record','child_goal')),
            description TEXT,
            position INTEGER NOT NULL DEFAULT 0,
            weight NUMERIC(16,4) NOT NULL DEFAULT 1 CHECK (weight > 0),
            progress_bearing BOOLEAN NOT NULL DEFAULT TRUE,
            completion_gate BOOLEAN NOT NULL DEFAULT FALSE,
            detached BOOLEAN NOT NULL DEFAULT FALSE,
            CHECK (parent_id IS NULL OR parent_id <> id)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_goal_roadmap_node_goal_id ON goal_roadmap_node(goal_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_goal_roadmap_node_parent ON goal_roadmap_node(parent_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_goal_roadmap_node_target ON goal_roadmap_node(target_id)")


def downgrade():
    # An empty graph can be removed for historical deep migration tests.
    # Accepted graph rows are retained when moving the pointer to 0080.
    if sa.inspect(op.get_bind()).has_table("goal_roadmap_node"):
        count = op.get_bind().execute(sa.text("SELECT count(*) FROM goal_roadmap_node")).scalar()
        if count == 0:
            op.execute("DROP TABLE goal_roadmap_node")
