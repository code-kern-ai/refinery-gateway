"""adds spreadsheet schema

Revision ID: d9e3947a51b5
Revises: 7edb03b88c03
Create Date: 2024-04-21 10:16:30.494398

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd9e3947a51b5'
down_revision = '7edb03b88c03'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.create_table(
        'spreadsheet_schema',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('cognition_project_id',  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('data_type', sa.String(), nullable=True),
        sa.Column('is_input', sa.Boolean(), nullable=True),
        sa.Column('is_hidden', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['cognition_project_id'], ['cognition.project.id'], ondelete='CASCADE'),
        schema='cognition'
    )
    op.create_index(op.f('ix_spreadsheet_schema_project_id'), 'spreadsheet_schema', ['cognition_project_id'], unique=False, schema='cognition')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    
    op.drop_index(op.f('ix_spreadsheet_schema_project_id'), table_name='spreadsheet_schema', schema='cognition')
    op.drop_table('spreadsheet_schema', schema='cognition')

    # ### end Alembic commands ###
