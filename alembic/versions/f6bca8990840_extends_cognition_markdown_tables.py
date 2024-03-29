"""extends cognition markdown tables

Revision ID: f6bca8990840
Revises: 3d0e01981f06
Create Date: 2023-12-20 10:54:14.354971

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f6bca8990840"
down_revision = "3d0e01981f06"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "markdown_dataset",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("refinery_project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "environment_variable_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("tokenizer", sa.String(), nullable=True),
        sa.Column("category_origin", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["environment_variable_id"],
            ["cognition.environment_variable.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["refinery_project_id"], ["project.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
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
        op.f("ix_cognition_markdown_dataset_environment_variable_id"),
        "markdown_dataset",
        ["environment_variable_id"],
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
    op.create_index(
        op.f("ix_cognition_markdown_dataset_refinery_project_id"),
        "markdown_dataset",
        ["refinery_project_id"],
        unique=False,
        schema="cognition",
    )
    op.create_table(
        "markdown_llm_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("markdown_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("model_used", sa.String(), nullable=True),
        sa.Column("input", sa.String(), nullable=True),
        sa.Column("output", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["markdown_file_id"], ["cognition.markdown_file.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="cognition",
    )
    op.create_index(
        op.f("ix_cognition_markdown_llm_logs_markdown_file_id"),
        "markdown_llm_logs",
        ["markdown_file_id"],
        unique=False,
        schema="cognition",
    )
    op.add_column(
        "environment_variable",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="cognition",
    )
    op.create_index(
        op.f("ix_cognition_environment_variable_organization_id"),
        "environment_variable",
        ["organization_id"],
        unique=False,
        schema="cognition",
    )
    op.create_foreign_key(
        None,
        "environment_variable",
        "organization",
        ["organization_id"],
        ["id"],
        source_schema="cognition",
        ondelete="CASCADE",
    )
    op.add_column(
        "markdown_file",
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="cognition",
    )
    op.add_column(
        "markdown_file",
        sa.Column("started_at", sa.DateTime(), nullable=True),
        schema="cognition",
    )
    op.add_column(
        "markdown_file",
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        schema="cognition",
    )
    op.add_column(
        "markdown_file",
        sa.Column("state", sa.String(), nullable=True),
        schema="cognition",
    )
    op.create_index(
        op.f("ix_cognition_markdown_file_dataset_id"),
        "markdown_file",
        ["dataset_id"],
        unique=False,
        schema="cognition",
    )
    op.create_foreign_key(
        None,
        "markdown_file",
        "markdown_dataset",
        ["dataset_id"],
        ["id"],
        source_schema="cognition",
        referent_schema="cognition",
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "markdown_file", schema="cognition", type_="foreignkey")
    op.drop_index(
        op.f("ix_cognition_markdown_file_dataset_id"),
        table_name="markdown_file",
        schema="cognition",
    )
    op.drop_column("markdown_file", "state", schema="cognition")
    op.drop_column("markdown_file", "finished_at", schema="cognition")
    op.drop_column("markdown_file", "started_at", schema="cognition")
    op.drop_column("markdown_file", "dataset_id", schema="cognition")
    op.drop_constraint(
        None, "environment_variable", schema="cognition", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_cognition_environment_variable_organization_id"),
        table_name="environment_variable",
        schema="cognition",
    )
    op.drop_column("environment_variable", "organization_id", schema="cognition")
    op.drop_index(
        op.f("ix_cognition_markdown_llm_logs_markdown_file_id"),
        table_name="markdown_llm_logs",
        schema="cognition",
    )
    op.drop_table("markdown_llm_logs", schema="cognition")
    op.drop_index(
        op.f("ix_cognition_markdown_dataset_refinery_project_id"),
        table_name="markdown_dataset",
        schema="cognition",
    )
    op.drop_index(
        op.f("ix_cognition_markdown_dataset_organization_id"),
        table_name="markdown_dataset",
        schema="cognition",
    )
    op.drop_index(
        op.f("ix_cognition_markdown_dataset_environment_variable_id"),
        table_name="markdown_dataset",
        schema="cognition",
    )
    op.drop_index(
        op.f("ix_cognition_markdown_dataset_created_by"),
        table_name="markdown_dataset",
        schema="cognition",
    )
    op.drop_table("markdown_dataset", schema="cognition")
    # ### end Alembic commands ###
