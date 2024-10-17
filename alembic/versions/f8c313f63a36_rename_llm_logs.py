"""rename llm logs

Revision ID: f8c313f63a36
Revises: c626887031f6
Create Date: 2024-10-15 16:01:26.391244

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f8c313f63a36'
down_revision = 'c626887031f6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('file_transformation_llm_logs',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('file_transformation_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('model_used', sa.String(), nullable=True),
    sa.Column('input', sa.String(), nullable=True),
    sa.Column('output', sa.String(), nullable=True),
    sa.Column('error', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['file_transformation_id'], ['cognition.file_transformation.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_file_transformation_llm_logs_file_transformation_id'), 'file_transformation_llm_logs', ['file_transformation_id'], unique=False, schema='cognition')
    op.drop_index('ix_cognition_markdown_llm_logs_markdown_file_id', table_name='markdown_llm_logs', schema='cognition')
    op.drop_table('markdown_llm_logs', schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('markdown_llm_logs',
    sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('markdown_file_id', postgresql.UUID(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('finished_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('model_used', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('input', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('output', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('error', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['markdown_file_id'], ['cognition.markdown_file.id'], name='markdown_llm_logs_markdown_file_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='markdown_llm_logs_pkey'),
    schema='cognition'
    )
    op.create_index('ix_cognition_markdown_llm_logs_markdown_file_id', 'markdown_llm_logs', ['markdown_file_id'], unique=False, schema='cognition')
    op.drop_index(op.f('ix_cognition_file_transformation_llm_logs_file_transformation_id'), table_name='file_transformation_llm_logs', schema='cognition')
    op.drop_table('file_transformation_llm_logs', schema='cognition')
    # ### end Alembic commands ###