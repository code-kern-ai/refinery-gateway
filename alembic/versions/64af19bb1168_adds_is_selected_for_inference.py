"""adds is_selected_for_inference

Revision ID: 64af19bb1168
Revises: 87f463aa5112
Create Date: 2022-11-10 14:28:47.549921

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "64af19bb1168"
down_revision = "87f463aa5112"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "attribute", sa.Column("is_selected_for_inference", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "embedding", sa.Column("is_selected_for_inference", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "information_source",
        sa.Column("is_selected_for_inference", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "labeling_task",
        sa.Column("is_selected_for_inference", sa.Boolean(), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("labeling_task", "is_selected_for_inference")
    op.drop_column("information_source", "is_selected_for_inference")
    op.drop_column("embedding", "is_selected_for_inference")
    op.drop_column("attribute", "is_selected_for_inference")
    # ### end Alembic commands ###
