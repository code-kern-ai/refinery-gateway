"""Added order number for strategies

Revision ID: 1118c7327b96
Revises: 414c990688f3
Create Date: 2024-10-10 15:15:29.164393

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1118c7327b96'
down_revision = '414c990688f3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('strategy', sa.Column('order', sa.Integer(), nullable=True), schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('strategy', 'order', schema='cognition')
    # ### end Alembic commands ###