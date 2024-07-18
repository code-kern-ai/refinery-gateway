"""Added language to project

Revision ID: 5238d19fec04
Revises: 0d587af700ce
Create Date: 2024-07-18 14:23:49.881922

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5238d19fec04'
down_revision = '0d587af700ce'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('tokenizer', sa.String(), nullable=True), schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('project', 'tokenizer', schema='cognition')
    # ### end Alembic commands ###
