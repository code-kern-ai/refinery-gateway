"""Add cross_selling table and cross_selling_id to organization

Revision ID: a1b2c3d4e5f6
Revises: 9a8abc15a493
Create Date: 2026-02-10

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "9a8abc15a493"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cross_selling",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "organization",
        sa.Column(
            "cross_selling_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "organization_cross_selling_id_fkey",
        "organization",
        "cross_selling",
        ["cross_selling_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_organization_cross_selling_id"),
        "organization",
        ["cross_selling_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_organization_cross_selling_id"),
        table_name="organization",
    )
    op.drop_constraint(
        "organization_cross_selling_id_fkey",
        "organization",
        type_="foreignkey",
    )
    op.drop_column("organization", "cross_selling_id")
    op.drop_table("cross_selling")
