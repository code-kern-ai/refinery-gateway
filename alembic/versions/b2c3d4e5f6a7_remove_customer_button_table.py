"""Remove customer_button table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-12

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index(
        op.f("ix_global_customer_button_organization_id"),
        table_name="customer_button",
        schema="global",
    )
    op.drop_index(
        op.f("ix_global_customer_button_created_by"),
        table_name="customer_button",
        schema="global",
    )
    op.drop_table("customer_button", schema="global")


def downgrade():
    op.create_table(
        "customer_button",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("visible", sa.Boolean(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="global",
    )
    op.create_index(
        op.f("ix_global_customer_button_created_by"),
        "customer_button",
        ["created_by"],
        unique=False,
        schema="global",
    )
    op.create_index(
        op.f("ix_global_customer_button_organization_id"),
        "customer_button",
        ["organization_id"],
        unique=False,
        schema="global",
    )
