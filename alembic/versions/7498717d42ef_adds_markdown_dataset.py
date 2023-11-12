"""adds markdown dataset

Revision ID: 7498717d42ef
Revises: 9ec726915d3c
Create Date: 2023-11-12 12:07:55.382820

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7498717d42ef'
down_revision = '9ec726915d3c'
branch_labels = None
depends_on = None

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("markdown_file", sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True), schema="cognition")

    op.create_table(
        "markdown_dataset",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("category_origin", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="cognition",
    )
    
    op.create_foreign_key(
        None,
        "markdown_file", 
        "markdown_dataset",
        ["dataset_id"],
        ["id"], 
        ondelete="CASCADE", 
        source_schema="cognition",
        referent_schema="cognition"
    )
    
    op.create_index(
        op.f("ix_cognition_markdown_file_dataset_id"),
        "markdown_file",
        ["dataset_id"],
        unique=False,
        schema="cognition",
    )

    op.create_index(
        op.f("ix_cognition_markdown_dataset_created_by"),
        "markdown_dataset",
        ["created_by"],
        unique=False,
        schema="cognition",
    )

    op.create_index(
        op.f("ix_cognition_markdown_dataset_organization_id"),
        "markdown_dataset",
        ["organization_id"],
        unique=False,
        schema="cognition",
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.drop_index(
        op.f("ix_cognition_markdown_file_dataset_id"),
        table_name="markdown_file",
        schema="cognition",
    )

    op.drop_constraint(None, "markdown_file", type_="foreignkey", schema="cognition")
    op.drop_column("markdown_file", "dataset_id", schema="cognition")
    
    op.drop_index(
        op.f("ix_cognition_markdown_dataset_created_by"),
        table_name="markdown_dataset",
        schema="cognition",
    )

    op.drop_index(
        op.f("ix_cognition_markdown_dataset_organization_id"),
        table_name="markdown_dataset",
        schema="cognition",
    )
    op.drop_table("markdown_dataset", schema="cognition")

    # ### end Alembic commands ###
