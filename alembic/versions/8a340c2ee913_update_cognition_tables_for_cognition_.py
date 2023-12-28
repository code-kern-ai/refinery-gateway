"""update cognition tables for cognition-apps

Revision ID: 8a340c2ee913
Revises: f6bca8990840
Create Date: 2023-12-24 01:16:44.644352

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a340c2ee913'
down_revision = 'f6bca8990840'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.add_column('message', sa.Column('feedback_value', sa.String(), nullable=True), schema='cognition')
    op.add_column('message', sa.Column('feedback_category', sa.String(), nullable=True), schema='cognition')
    op.add_column('message', sa.Column('selection_widget', sa.ARRAY(sa.JSON()), nullable=True), schema='cognition')
    
    op.add_column('conversation', sa.Column('header', sa.String(), nullable=True), schema='cognition')

    op.add_column('strategy_step', sa.Column('progress_text', sa.String(), nullable=True), schema='cognition')
    op.add_column('strategy_step', sa.Column('enable_emissions', sa.Boolean(), nullable=True), schema='cognition')
    op.add_column('strategy_step', sa.Column('execute_if_source_code', sa.String(), nullable=True), schema='cognition')

    op.add_column('pipeline_logs', sa.Column('skipped_step', sa.Boolean(), nullable=True), schema='cognition')

    op.add_column('project', sa.Column('interface_type', sa.String(), nullable=True), schema='cognition')
    op.add_column('project', sa.Column('execute_query_enrichment_if_source_code', sa.String(), nullable=True), schema='cognition')
    op.add_column('project', sa.Column('customer_color_primary', sa.String(), nullable=True), schema='cognition')
    op.add_column('project', sa.Column('customer_color_primary_only_accent', sa.Boolean(), nullable=True), schema='cognition')
    op.add_column('project', sa.Column('customer_color_secondary', sa.String(), nullable=True), schema='cognition')

    op.add_column('user', sa.Column('language_display', sa.String(), nullable=True))

    op.drop_column('message', 'positive_feedback', schema='cognition')
    
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.add_column('message', sa.Column('positive_feedback', sa.Boolean(), nullable=True), schema='cognition')

    op.drop_column('user', 'language_display')

    op.drop_column('project', 'execute_query_enrichment_if_source_code', schema='cognition')
    op.drop_column('project', 'interface_type', schema='cognition')
    op.drop_column('project', 'customer_color_primary', schema='cognition')
    op.drop_column('project', 'customer_color_secondary', schema='cognition')

    op.drop_column('pipeline_logs', 'skipped_step', schema='cognition')
    
    op.drop_column('strategy_step', 'execute_if_source_code', schema='cognition')
    op.drop_column('strategy_step', 'enable_emissions', schema='cognition')
    op.drop_column('strategy_step', 'progress_text', schema='cognition')

    op.drop_column('conversation', 'header', schema='cognition')
    
    op.drop_column('message', 'feedback_category', schema='cognition')
    op.drop_column('message', 'feedback_value', schema='cognition')
    op.drop_column('message', 'selection_widget', schema='cognition')

    # ### end Alembic commands ###
