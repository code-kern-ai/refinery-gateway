"""Adds admin message

Revision ID: 16024ceb543f
Revises: 0e0e4aeac7eb
Create Date: 2023-02-21 16:49:34.889903

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '16024ceb543f'
down_revision = '0e0e4aeac7eb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admin_message',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('text', sa.String(), nullable=True),
    sa.Column('level', sa.String(), nullable=True),
    sa.Column('archived', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('archive_date', sa.DateTime(), nullable=True),
    sa.Column('archived_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('archived_reason', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['archived_by'], ['user.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_message_archived_by'), 'admin_message', ['archived_by'], unique=False)
    op.create_index(op.f('ix_admin_message_created_by'), 'admin_message', ['created_by'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_admin_message_created_by'), table_name='admin_message')
    op.drop_index(op.f('ix_admin_message_archived_by'), table_name='admin_message')
    op.drop_table('admin_message')
    # ### end Alembic commands ###