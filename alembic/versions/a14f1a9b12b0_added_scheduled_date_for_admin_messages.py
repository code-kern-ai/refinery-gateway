"""Added scheduled date for admin messages

Revision ID: a14f1a9b12b0
Revises: 63364f1fe61d
Create Date: 2024-05-22 11:51:57.614264

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a14f1a9b12b0'
down_revision = '63364f1fe61d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('admin_message', sa.Column('scheduled_date', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('admin_message', 'scheduled_date')
    # ### end Alembic commands ###