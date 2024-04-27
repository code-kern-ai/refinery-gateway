"""adds cognition actions table

Revision ID: 588c5e9f90aa
Revises: 7edb03b88c03
Create Date: 2024-04-27 08:59:52.899815

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '588c5e9f90aa'
down_revision = '7edb03b88c03'
branch_labels = None
depends_on = None

# class CognitionAction(Base):
#     __tablename__ = Tablenames.ACTION.value
#     __table_args__ = {"schema": "cognition"}
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     project_id = Column(
#         UUID(as_uuid=True),
#         ForeignKey(f"cognition.{Tablenames.PROJECT.value}.id", ondelete="CASCADE"),
#         index=True,
#     )
#     created_by = Column(
#         UUID(as_uuid=True),
#         ForeignKey(f"{Tablenames.USER.value}.id", ondelete="SET NULL"),
#         index=True,
#     )
#     created_at = Column(DateTime, default=sql.func.now())
#     name = Column(String)
#     description = Column(String)
#     questions = Column(ARRAY(String))
#     on_enter_send_message = Column(Boolean, default=False)

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "action",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(), nullable=True, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("questions", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("on_enter_send_message", sa.Boolean(), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["cognition.project.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="cognition",
    )
    op.create_index(op.f("ix_action_created_at"), "action", ["created_at"], unique=False, schema="cognition")
    op.create_index(op.f("ix_action_created_by"), "action", ["created_by"], unique=False, schema="cognition")
    op.create_index(op.f("ix_action_project_id"), "action", ["project_id"], unique=False, schema="cognition")

    op.add_column(
        "conversation",
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="cognition",
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("conversation", "action_id", schema="cognition")

    op.drop_index(op.f("ix_action_project_id"), table_name="action", schema="cognition")
    op.drop_index(op.f("ix_action_created_by"), table_name="action", schema="cognition")
    op.drop_index(op.f("ix_action_created_at"), table_name="action", schema="cognition")
    op.drop_table("action", schema="cognition")
    # ### end Alembic commands ###
