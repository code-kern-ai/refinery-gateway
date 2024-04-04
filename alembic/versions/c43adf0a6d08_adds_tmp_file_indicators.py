"""Adds tmp file indicators


Revision ID: c43adf0a6d08
Revises: 4861b97fcd5d
Create Date: 2024-04-03 12:04:17.717913

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c43adf0a6d08'
down_revision = '4861b97fcd5d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('conversation', sa.Column('has_tmp_files', sa.Boolean(), nullable=True), schema='cognition')
    op.add_column('project', sa.Column('allow_file_upload', sa.Boolean(), nullable=True), schema='cognition')
    op.add_column('project', sa.Column('max_file_size_mb', sa.Float(), nullable=True), schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('project', 'allow_file_upload', schema='cognition')
    op.drop_column('project', 'max_file_size_mb', schema='cognition')
    op.drop_column('conversation', 'has_tmp_files', schema='cognition')
    # ### end Alembic commands ###
