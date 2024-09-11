"""Remove refinery token table

Revision ID: 414c990688f3
Revises: 3e59ce51739c
Create Date: 2024-09-09 09:25:36.796509

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '414c990688f3'
down_revision = '3e59ce51739c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    # ------------------------ pat remove ------------------------
    ## TODO: remove migration to dummy table logic before merge to dev
    connection = op.get_bind()
    connection.execute("DROP TABLE IF EXISTS migration_pat_dummy")
    connection.execute("SELECT * INTO migration_pat_dummy FROM personal_access_token")

    # generated code
    op.drop_index('ix_personal_access_token_project_id', table_name='personal_access_token')
    op.drop_index('ix_personal_access_token_user_id', table_name='personal_access_token')
    op.drop_table('personal_access_token')

    # ------------------------ cognition table fields ------------------------
    ## TODO: remove migration to dummy table logic before merge to dev
    # connection = op.get_bind()
    connection.execute("DROP TABLE IF EXISTS migration_project_dummy")
    connection.execute("SELECT id, refinery_references_project_id, refinery_question_project_id,refinery_relevance_project_id, refinery_synchronization_interval_option,execute_query_enrichment_if_source_code INTO migration_project_dummy FROM cognition.project")


    op.drop_index('ix_cognition_project_refinery_question_project_id', table_name='project', schema='cognition')
    op.drop_index('ix_cognition_project_refinery_references_project_id', table_name='project', schema='cognition')
    op.drop_index('ix_cognition_project_refinery_relevance_project_id', table_name='project', schema='cognition')
    op.drop_constraint('project_refinery_references_project_id_fkey', 'project', schema='cognition', type_='foreignkey')
    op.drop_constraint('project_refinery_question_project_id_fkey', 'project', schema='cognition', type_='foreignkey')
    op.drop_constraint('project_refinery_relevance_project_id_fkey', 'project', schema='cognition', type_='foreignkey')
    op.drop_column('project', 'refinery_references_project_id', schema='cognition')
    op.drop_column('project', 'refinery_synchronization_interval_option', schema='cognition')
    op.drop_column('project', 'refinery_question_project_id', schema='cognition')
    op.drop_column('project', 'refinery_relevance_project_id', schema='cognition')
    op.drop_column('project', 'execute_query_enrichment_if_source_code', schema='cognition')

    # ------------------------ sync table ------------------------	
    connection.execute("DROP TABLE IF EXISTS migration_sync_dummy")
    connection.execute("SELECT * INTO migration_sync_dummy FROM cognition.refinery_synchronization_task")
    
    op.drop_index('ix_cognition_refinery_synchronization_task_cognition_project_id', table_name='refinery_synchronization_task', schema='cognition')
    op.drop_index('ix_cognition_refinery_synchronization_task_created_by', table_name='refinery_synchronization_task', schema='cognition')
    op.drop_index('ix_cognition_refinery_synchronization_task_refinery_project_id', table_name='refinery_synchronization_task', schema='cognition')
    op.drop_table('refinery_synchronization_task', schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    
    # ------------------------ pat remove ------------------------
    op.create_table('personal_access_token',
    sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('project_id', postgresql.UUID(), autoincrement=False, nullable=True),
    sa.Column('user_id', postgresql.UUID(), autoincrement=False, nullable=True),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('scope', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('last_used', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('token', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], name='personal_access_token_project_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='personal_access_token_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='personal_access_token_pkey')
    )
    op.create_index('ix_personal_access_token_user_id', 'personal_access_token', ['user_id'], unique=False)
    op.create_index('ix_personal_access_token_project_id', 'personal_access_token', ['project_id'], unique=False)

    ## TODO: remove migration to dummy table logic before merge to dev
    connection = op.get_bind()
    connection.execute("INSERT INTO personal_access_token SELECT * FROM migration_pat_dummy")
    connection.execute("DROP TABLE IF EXISTS migration_pat_dummy")

    # ------------------------ cognition table fields ------------------------

    op.add_column('project', sa.Column('execute_query_enrichment_if_source_code', sa.VARCHAR(), autoincrement=False, nullable=True), schema='cognition')
    op.add_column('project', sa.Column('refinery_relevance_project_id', postgresql.UUID(), autoincrement=False, nullable=True), schema='cognition')
    op.add_column('project', sa.Column('refinery_question_project_id', postgresql.UUID(), autoincrement=False, nullable=True), schema='cognition')
    op.add_column('project', sa.Column('refinery_synchronization_interval_option', sa.VARCHAR(), autoincrement=False, nullable=True), schema='cognition')
    op.add_column('project', sa.Column('refinery_references_project_id', postgresql.UUID(), autoincrement=False, nullable=True), schema='cognition')
    op.create_foreign_key('project_refinery_relevance_project_id_fkey', 'project', 'project', ['refinery_relevance_project_id'], ['id'], source_schema='cognition', ondelete='SET NULL')
    op.create_foreign_key('project_refinery_question_project_id_fkey', 'project', 'project', ['refinery_question_project_id'], ['id'], source_schema='cognition', ondelete='SET NULL')
    op.create_foreign_key('project_refinery_references_project_id_fkey', 'project', 'project', ['refinery_references_project_id'], ['id'], source_schema='cognition', ondelete='SET NULL')
    op.create_index('ix_cognition_project_refinery_relevance_project_id', 'project', ['refinery_relevance_project_id'], unique=False, schema='cognition')
    op.create_index('ix_cognition_project_refinery_references_project_id', 'project', ['refinery_references_project_id'], unique=False, schema='cognition')
    op.create_index('ix_cognition_project_refinery_question_project_id', 'project', ['refinery_question_project_id'], unique=False, schema='cognition')

    connection.execute("""UPDATE cognition.project p
            SET refinery_references_project_id = m.refinery_references_project_id,
                refinery_question_project_id=m.refinery_question_project_id,
                refinery_relevance_project_id = m.refinery_relevance_project_id,
                refinery_synchronization_interval_option = m.refinery_synchronization_interval_option,
                execute_query_enrichment_if_source_code = m.execute_query_enrichment_if_source_code
        FROM cognition.migration_project_dummy m
        WHERE p.id = m.id;""")
    connection.execute("DROP TABLE IF EXISTS migration_project_dummy")
    
    # ------------------------ sync table ------------------------	

    op.create_table('refinery_synchronization_task',
    sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('cognition_project_id', postgresql.UUID(), autoincrement=False, nullable=True),
    sa.Column('refinery_project_id', postgresql.UUID(), autoincrement=False, nullable=True),
    sa.Column('created_by', postgresql.UUID(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('finished_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('state', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('logs', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
    sa.Column('num_records_created', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['cognition_project_id'], ['cognition.project.id'], name='refinery_synchronization_task_cognition_project_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], name='refinery_synchronization_task_created_by_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['refinery_project_id'], ['project.id'], name='refinery_synchronization_task_refinery_project_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='refinery_synchronization_task_pkey'),
    schema='cognition'
    )
    op.create_index('ix_cognition_refinery_synchronization_task_refinery_project_id', 'refinery_synchronization_task', ['refinery_project_id'], unique=False, schema='cognition')
    op.create_index('ix_cognition_refinery_synchronization_task_created_by', 'refinery_synchronization_task', ['created_by'], unique=False, schema='cognition')
    op.create_index('ix_cognition_refinery_synchronization_task_cognition_project_id', 'refinery_synchronization_task', ['cognition_project_id'], unique=False, schema='cognition')

    connection.execute("INSERT INTO cognition.refinery_synchronization_task SELECT * FROM migration_sync_dummy")
    connection.execute("DROP TABLE IF EXISTS migration_sync_dummy")

    # ### end Alembic commands ###
