"""refactor cognition strategy step

Revision ID: 3d0e01981f06
Revises: 491ea68a7baf
Create Date: 2023-12-05 10:38:21.403038

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3d0e01981f06"
down_revision = "491ea68a7baf"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        "ix_cognition_python_step_created_by",
        table_name="python_step",
        schema="cognition",
    )
    op.drop_index(
        "ix_cognition_python_step_project_id",
        table_name="python_step",
        schema="cognition",
    )
    op.drop_index(
        "ix_cognition_python_step_strategy_step_id",
        table_name="python_step",
        schema="cognition",
    )
    op.drop_table("python_step", schema="cognition")
    op.drop_index(
        "ix_cognition_retriever_part_created_by",
        table_name="retriever_part",
        schema="cognition",
    )
    op.drop_index(
        "ix_cognition_retriever_part_project_id",
        table_name="retriever_part",
        schema="cognition",
    )
    op.drop_index(
        "ix_cognition_retriever_part_retriever_id",
        table_name="retriever_part",
        schema="cognition",
    )
    op.drop_table("retriever_part", schema="cognition")
    op.drop_index(
        "ix_cognition_retriever_created_by", table_name="retriever", schema="cognition"
    )
    op.drop_index(
        "ix_cognition_retriever_project_id", table_name="retriever", schema="cognition"
    )
    op.drop_index(
        "ix_cognition_retriever_strategy_step_id",
        table_name="retriever",
        schema="cognition",
    )
    op.drop_table("retriever", schema="cognition")
    op.drop_index(
        "ix_cognition_llm_step_created_by", table_name="llm_step", schema="cognition"
    )
    op.drop_index(
        "ix_cognition_llm_step_project_id", table_name="llm_step", schema="cognition"
    )
    op.drop_index(
        "ix_cognition_llm_step_strategy_step_id",
        table_name="llm_step",
        schema="cognition",
    )
    op.drop_table("llm_step", schema="cognition")
    op.add_column(
        "strategy_step",
        sa.Column("step_type", sa.String(), nullable=True),
        schema="cognition",
    )
    op.add_column(
        "strategy_step",
        sa.Column("position", sa.Integer(), nullable=True),
        schema="cognition",
    )
    op.add_column(
        "strategy_step",
        sa.Column("config", sa.JSON(), nullable=True),
        schema="cognition",
    )
    op.drop_column("strategy_step", "strategy_step_position", schema="cognition")
    op.drop_column("strategy_step", "strategy_step_type", schema="cognition")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "strategy_step",
        sa.Column(
            "strategy_step_type", sa.VARCHAR(), autoincrement=False, nullable=True
        ),
        schema="cognition",
    )
    op.add_column(
        "strategy_step",
        sa.Column(
            "strategy_step_position", sa.INTEGER(), autoincrement=False, nullable=True
        ),
        schema="cognition",
    )
    op.drop_column("strategy_step", "config", schema="cognition")
    op.drop_column("strategy_step", "position", schema="cognition")
    op.drop_column("strategy_step", "step_type", schema="cognition")
    op.create_table(
        "llm_step",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("project_id", postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "strategy_step_id", postgresql.UUID(), autoincrement=False, nullable=True
        ),
        sa.Column("created_by", postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("llm_identifier", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column(
            "llm_config",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("template_prompt", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("question_prompt", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="llm_step_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["cognition.project.id"],
            name="llm_step_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_step_id"],
            ["cognition.strategy_step.id"],
            name="llm_step_strategy_step_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="llm_step_pkey"),
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_llm_step_strategy_step_id",
        "llm_step",
        ["strategy_step_id"],
        unique=False,
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_llm_step_project_id",
        "llm_step",
        ["project_id"],
        unique=False,
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_llm_step_created_by",
        "llm_step",
        ["created_by"],
        unique=False,
        schema="cognition",
    )
    op.create_table(
        "retriever",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("project_id", postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "strategy_step_id", postgresql.UUID(), autoincrement=False, nullable=True
        ),
        sa.Column("created_by", postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "search_input_field", sa.VARCHAR(), autoincrement=False, nullable=True
        ),
        sa.Column("meta_data", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="retriever_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["cognition.project.id"],
            name="retriever_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_step_id"],
            ["cognition.strategy_step.id"],
            name="retriever_strategy_step_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="retriever_pkey"),
        schema="cognition",
        postgresql_ignore_search_path=False,
    )
    op.create_index(
        "ix_cognition_retriever_strategy_step_id",
        "retriever",
        ["strategy_step_id"],
        unique=False,
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_retriever_project_id",
        "retriever",
        ["project_id"],
        unique=False,
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_retriever_created_by",
        "retriever",
        ["created_by"],
        unique=False,
        schema="cognition",
    )
    op.create_table(
        "retriever_part",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("project_id", postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "retriever_id", postgresql.UUID(), autoincrement=False, nullable=True
        ),
        sa.Column("created_by", postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("embedding_name", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("number_records", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("enabled", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="retriever_part_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["cognition.project.id"],
            name="retriever_part_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["retriever_id"],
            ["cognition.retriever.id"],
            name="retriever_part_retriever_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="retriever_part_pkey"),
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_retriever_part_retriever_id",
        "retriever_part",
        ["retriever_id"],
        unique=False,
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_retriever_part_project_id",
        "retriever_part",
        ["project_id"],
        unique=False,
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_retriever_part_created_by",
        "retriever_part",
        ["created_by"],
        unique=False,
        schema="cognition",
    )
    op.create_table(
        "python_step",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("project_id", postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "strategy_step_id", postgresql.UUID(), autoincrement=False, nullable=True
        ),
        sa.Column("created_by", postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("source_code", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="python_step_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["cognition.project.id"],
            name="python_step_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_step_id"],
            ["cognition.strategy_step.id"],
            name="python_step_strategy_step_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="python_step_pkey"),
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_python_step_strategy_step_id",
        "python_step",
        ["strategy_step_id"],
        unique=False,
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_python_step_project_id",
        "python_step",
        ["project_id"],
        unique=False,
        schema="cognition",
    )
    op.create_index(
        "ix_cognition_python_step_created_by",
        "python_step",
        ["created_by"],
        unique=False,
        schema="cognition",
    )
    # ### end Alembic commands ###
