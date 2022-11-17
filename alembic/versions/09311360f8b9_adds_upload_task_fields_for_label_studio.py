"""Adds upload task fields for label studio

Revision ID: 09311360f8b9
Revises: 87f463aa5112
Create Date: 2022-11-07 10:32:10.881495

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '09311360f8b9'
down_revision = '87f463aa5112'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('upload_task', sa.Column('upload_type', sa.String(), nullable=True))
    op.add_column('upload_task', sa.Column('file_additional_info', sa.String(), nullable=True))
    op.add_column('upload_task', sa.Column('mappings', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('upload_task', 'user_mapping')
    op.drop_column('upload_task', 'file_additional_info')
    op.drop_column('upload_task', 'upload_type')
    # ### end Alembic commands ###
