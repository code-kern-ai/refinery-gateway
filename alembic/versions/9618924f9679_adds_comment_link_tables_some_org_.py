"""Adds comment & link tables & some org management

Revision ID: 9618924f9679
Revises: 5b3a4deea1c4
Create Date: 2022-09-15 07:15:02.934928

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9618924f9679"
down_revision = "5b3a4deea1c4"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "comment_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("xfkey", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("xftype", sa.String(), nullable=True),
        sa.Column("order_key", sa.Integer(), autoincrement=True, nullable=True),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("is_markdown", sa.Boolean(), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_comment_data_created_by"), "comment_data", ["created_by"], unique=False
    )
    op.create_index(
        op.f("ix_comment_data_project_id"), "comment_data", ["project_id"], unique=False
    )
    op.create_index(
        op.f("ix_comment_data_xfkey"), "comment_data", ["xfkey"], unique=False
    )
    op.create_index(
        op.f("ix_comment_data_xftype"), "comment_data", ["xftype"], unique=False
    )
    op.create_table(
        "labeling_access_link",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("link", sa.String(), nullable=True),
        sa.Column("data_slice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("heuristic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("link_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["data_slice_id"], ["data_slice.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["heuristic_id"], ["information_source.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_labeling_access_link_project_id"),
        "labeling_access_link",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labeling_access_link_created_by"),
        "labeling_access_link",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labeling_access_link_data_slice_id"),
        "labeling_access_link",
        ["data_slice_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labeling_access_link_heuristic_id"),
        "labeling_access_link",
        ["heuristic_id"],
        unique=False,
    )
    op.add_column("organization", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("organization", sa.Column("is_paying", sa.Boolean(), nullable=True))
    op.add_column("organization", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("role", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user", "role")
    op.drop_column("organization", "created_at")
    op.drop_column("organization", "is_paying")
    op.drop_column("organization", "started_at")
    op.drop_index(
        op.f("ix_labeling_access_link_project_id"), table_name="labeling_access_link"
    )
    op.drop_index(
        op.f("ix_labeling_access_link_heuristic_id"), table_name="labeling_access_link"
    )
    op.drop_index(
        op.f("ix_labeling_access_link_data_slice_id"), table_name="labeling_access_link"
    )
    op.drop_index(
        op.f("ix_labeling_access_link_created_by"), table_name="labeling_access_link"
    )
    op.drop_table("labeling_access_link")
    op.drop_index(op.f("ix_comment_data_xftype"), table_name="comment_data")
    op.drop_index(op.f("ix_comment_data_xfkey"), table_name="comment_data")
    op.drop_index(op.f("ix_comment_data_project_id"), table_name="comment_data")
    op.drop_index(op.f("ix_comment_data_created_by"), table_name="comment_data")
    op.drop_table("comment_data")
    # ### end Alembic commands ###
