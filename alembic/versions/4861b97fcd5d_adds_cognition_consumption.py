"""adds cognition consumption

Revision ID: 4861b97fcd5d
Revises: 754dd15f2c9c
Create Date: 2024-03-25 14:27:56.042650

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4861b97fcd5d'
down_revision = '754dd15f2c9c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('consumption_summary',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('creation_date', sa.Date(), nullable=True),
    sa.Column('project_name', sa.String(), nullable=True),
    sa.Column('complexity', sa.String(), nullable=True),
    sa.Column('count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['cognition.project.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'project_id', 'creation_date', 'complexity', name='unique_summary'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_consumption_summary_creation_date'), 'consumption_summary', ['creation_date'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_consumption_summary_organization_id'), 'consumption_summary', ['organization_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_consumption_summary_project_id'), 'consumption_summary', ['project_id'], unique=False, schema='cognition')
    op.create_table('consumption_log',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('complexity', sa.String(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('project_name', sa.String(), nullable=True),
    sa.Column('project_state', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['cognition.conversation.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['message_id'], ['cognition.message.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['cognition.project.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['strategy_id'], ['cognition.strategy.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_consumption_log_conversation_id'), 'consumption_log', ['conversation_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_consumption_log_created_by'), 'consumption_log', ['created_by'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_consumption_log_message_id'), 'consumption_log', ['message_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_consumption_log_organization_id'), 'consumption_log', ['organization_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_consumption_log_project_id'), 'consumption_log', ['project_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_consumption_log_strategy_id'), 'consumption_log', ['strategy_id'], unique=False, schema='cognition')
    op.add_column('project', sa.Column('state', sa.String(), nullable=True), schema='cognition')
    op.drop_column('project', 'wizard_running', schema='cognition')
    op.add_column('strategy', sa.Column('complexity', sa.String(), nullable=True), schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('strategy', 'complexity', schema='cognition')
    op.add_column('project', sa.Column('wizard_running', sa.BOOLEAN(), autoincrement=False, nullable=True), schema='cognition')
    op.drop_column('project', 'state', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_log_strategy_id'), table_name='consumption_log', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_log_project_id'), table_name='consumption_log', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_log_organization_id'), table_name='consumption_log', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_log_message_id'), table_name='consumption_log', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_log_created_by'), table_name='consumption_log', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_log_conversation_id'), table_name='consumption_log', schema='cognition')
    op.drop_table('consumption_log', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_summary_project_id'), table_name='consumption_summary', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_summary_organization_id'), table_name='consumption_summary', schema='cognition')
    op.drop_index(op.f('ix_cognition_consumption_summary_creation_date'), table_name='consumption_summary', schema='cognition')
    op.drop_table('consumption_summary', schema='cognition')
    # ### end Alembic commands ###
