"""ensured user cascade behaviour

Revision ID: 706d5611a73e
Revises: 194838aa0431
Create Date: 2024-06-12 09:29:07.617462

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '706d5611a73e'
down_revision = '194838aa0431'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('admin_message_archived_by_fkey', 'admin_message', type_='foreignkey')
    op.drop_constraint('admin_message_created_by_fkey', 'admin_message', type_='foreignkey')
    op.create_foreign_key(None, 'admin_message', 'user', ['archived_by'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(None, 'admin_message', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('agreement_user_id_fkey', 'agreement', type_='foreignkey')
    op.create_foreign_key(None, 'agreement', 'user', ['user_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('comment_data_created_by_fkey', 'comment_data', type_='foreignkey')
    op.create_foreign_key(None, 'comment_data', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('data_slice_created_by_fkey', 'data_slice', type_='foreignkey')
    op.create_foreign_key(None, 'data_slice', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('embedding_created_by_fkey', 'embedding', type_='foreignkey')
    op.create_foreign_key(None, 'embedding', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('information_source_created_by_fkey', 'information_source', type_='foreignkey')
    op.create_foreign_key(None, 'information_source', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('labeling_access_link_created_by_fkey', 'labeling_access_link', type_='foreignkey')
    op.create_foreign_key(None, 'labeling_access_link', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('labeling_task_label_created_by_fkey', 'labeling_task_label', type_='foreignkey')
    op.create_foreign_key(None, 'labeling_task_label', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('project_created_by_fkey', 'project', type_='foreignkey')
    op.create_foreign_key(None, 'project', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('record_label_association_created_by_fkey', 'record_label_association', type_='foreignkey')
    op.create_foreign_key(None, 'record_label_association', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_task_queue_created_by'), 'task_queue', ['created_by'], unique=False)
    op.drop_constraint('task_queue_created_by_fkey', 'task_queue', type_='foreignkey')
    op.create_foreign_key(None, 'task_queue', 'user', ['created_by'], ['id'], ondelete='SET NULL')
    op.drop_constraint('upload_task_user_id_fkey', 'upload_task', type_='foreignkey')
    op.create_foreign_key(None, 'upload_task', 'user', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_cognition_macro_execution_organization_id'), 'macro_execution', ['organization_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_macro_execution_link_organization_id'), 'macro_execution_link', ['organization_id'], unique=False, schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_cognition_macro_execution_link_organization_id'), table_name='macro_execution_link', schema='cognition')
    op.drop_index(op.f('ix_cognition_macro_execution_organization_id'), table_name='macro_execution', schema='cognition')
    op.drop_constraint(None, 'upload_task', type_='foreignkey')
    op.create_foreign_key('upload_task_user_id_fkey', 'upload_task', 'user', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'task_queue', type_='foreignkey')
    op.create_foreign_key('task_queue_created_by_fkey', 'task_queue', 'user', ['created_by'], ['id'])
    op.drop_index(op.f('ix_task_queue_created_by'), table_name='task_queue')
    op.drop_constraint(None, 'record_label_association', type_='foreignkey')
    op.create_foreign_key('record_label_association_created_by_fkey', 'record_label_association', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'project', type_='foreignkey')
    op.create_foreign_key('project_created_by_fkey', 'project', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'labeling_task_label', type_='foreignkey')
    op.create_foreign_key('labeling_task_label_created_by_fkey', 'labeling_task_label', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'labeling_access_link', type_='foreignkey')
    op.create_foreign_key('labeling_access_link_created_by_fkey', 'labeling_access_link', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'information_source', type_='foreignkey')
    op.create_foreign_key('information_source_created_by_fkey', 'information_source', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'embedding', type_='foreignkey')
    op.create_foreign_key('embedding_created_by_fkey', 'embedding', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'data_slice', type_='foreignkey')
    op.create_foreign_key('data_slice_created_by_fkey', 'data_slice', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'comment_data', type_='foreignkey')
    op.create_foreign_key('comment_data_created_by_fkey', 'comment_data', 'user', ['created_by'], ['id'])
    op.drop_constraint(None, 'agreement', type_='foreignkey')
    op.create_foreign_key('agreement_user_id_fkey', 'agreement', 'user', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'admin_message', type_='foreignkey')
    op.drop_constraint(None, 'admin_message', type_='foreignkey')
    op.create_foreign_key('admin_message_created_by_fkey', 'admin_message', 'user', ['created_by'], ['id'])
    op.create_foreign_key('admin_message_archived_by_fkey', 'admin_message', 'user', ['archived_by'], ['id'])
    # ### end Alembic commands ###
