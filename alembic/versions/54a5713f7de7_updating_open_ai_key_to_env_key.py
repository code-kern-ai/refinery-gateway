"""Updating open ai key to env key

Revision ID: 54a5713f7de7
Revises: a14f1a9b12b0
Create Date: 2024-05-31 11:21:07.130267

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '54a5713f7de7'
down_revision = 'a14f1a9b12b0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('env_var_id', postgresql.UUID(as_uuid=True), nullable=True), schema='cognition')
    op.drop_index('ix_cognition_project_open_ai_env_var_id', table_name='project', schema='cognition')
    op.create_index(op.f('ix_cognition_project_env_var_id'), 'project', ['env_var_id'], unique=False, schema='cognition')
    op.drop_constraint('project_open_ai_env_var_id_fkey', 'project', schema='cognition', type_='foreignkey')
    op.create_foreign_key(None, 'project', 'environment_variable', ['env_var_id'], ['id'], source_schema='cognition', referent_schema='cognition', ondelete='SET NULL')
    op.drop_column('project', 'open_ai_env_var_id', schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('open_ai_env_var_id', postgresql.UUID(), autoincrement=False, nullable=True), schema='cognition')
    op.drop_constraint(None, 'project', schema='cognition', type_='foreignkey')
    op.create_foreign_key('project_open_ai_env_var_id_fkey', 'project', 'environment_variable', ['open_ai_env_var_id'], ['id'], source_schema='cognition', referent_schema='cognition', ondelete='SET NULL')
    op.drop_index(op.f('ix_cognition_project_env_var_id'), table_name='project', schema='cognition')
    op.create_index('ix_cognition_project_open_ai_env_var_id', 'project', ['open_ai_env_var_id'], unique=False, schema='cognition')
    op.drop_column('project', 'env_var_id', schema='cognition')
    # ### end Alembic commands ###
