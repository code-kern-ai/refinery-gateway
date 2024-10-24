"""Macro tables

Revision ID: 194838aa0431
Revises: a14f1a9b12b0
Create Date: 2024-06-05 11:42:56.258816

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '194838aa0431'
down_revision = 'a14f1a9b12b0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('macro',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('macro_type', sa.String(), nullable=True),
    sa.Column('scope', sa.String(), nullable=True),
    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['cognition.project.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_macro_created_by'), 'macro', ['created_by'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_organization_id'), 'macro', ['organization_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_project_id'), 'macro', ['project_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_scope'), 'macro', ['scope'], unique=False, schema='cognition')
    op.create_table('macro_execution',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('macro_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('execution_group_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('meta_info', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['macro_id'], ['cognition.macro.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_macro_execution_created_by'), 'macro_execution', ['created_by'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_execution_execution_group_id'), 'macro_execution', ['execution_group_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_execution_macro_id'), 'macro_execution', ['macro_id'], unique=False, schema='cognition')
    op.create_table('macro_node',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('macro_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_root', sa.Boolean(), nullable=True),
    sa.Column('config', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['macro_id'], ['cognition.macro.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_macro_node_created_by'), 'macro_node', ['created_by'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_node_macro_id'), 'macro_node', ['macro_id'], unique=False, schema='cognition')
    op.create_table('macro_edge',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('macro_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('from_node_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('to_node_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('config', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['from_node_id'], ['cognition.macro_node.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['macro_id'], ['cognition.macro.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['to_node_id'], ['cognition.macro_node.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_macro_edge_created_by'), 'macro_edge', ['created_by'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_edge_from_node_id'), 'macro_edge', ['from_node_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_edge_macro_id'), 'macro_edge', ['macro_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_edge_to_node_id'), 'macro_edge', ['to_node_id'], unique=False, schema='cognition')
    op.create_table('macro_execution_link',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('execution_node_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('action', sa.String(), nullable=True),
    sa.Column('other_id_target', sa.String(), nullable=True),
    sa.Column('other_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.ForeignKeyConstraint(['execution_id'], ['cognition.macro_execution.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['execution_node_id'], ['cognition.macro_node.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_macro_execution_link_execution_id'), 'macro_execution_link', ['execution_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_execution_link_execution_node_id'), 'macro_execution_link', ['execution_node_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_execution_link_other_id'), 'macro_execution_link', ['other_id'], unique=False, schema='cognition')
    op.add_column('project', sa.Column('macro_config', sa.JSON(), nullable=True), schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('project', 'macro_config', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_execution_link_other_id'), table_name='macro_execution_link', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_execution_link_execution_node_id'), table_name='macro_execution_link', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_execution_link_execution_id'), table_name='macro_execution_link', schema='cognition')
    op.drop_table('macro_execution_link', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_edge_to_node_id'), table_name='macro_edge', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_edge_macro_id'), table_name='macro_edge', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_edge_from_node_id'), table_name='macro_edge', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_edge_created_by'), table_name='macro_edge', schema='cognition')
    op.drop_table('macro_edge', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_node_macro_id'), table_name='macro_node', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_node_created_by'), table_name='macro_node', schema='cognition')
    op.drop_table('macro_node', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_execution_macro_id'), table_name='macro_execution', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_execution_execution_group_id'), table_name='macro_execution', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_execution_created_by'), table_name='macro_execution', schema='cognition')
    op.drop_table('macro_execution', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_scope'), table_name='macro', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_project_id'), table_name='macro', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_organization_id'), table_name='macro', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_created_by'), table_name='macro', schema='cognition')
    op.drop_table('macro', schema='cognition')
    # ### end Alembic commands ###
