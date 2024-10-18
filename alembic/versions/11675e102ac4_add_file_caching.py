"""add file caching

Revision ID: 11675e102ac4
Revises: 1118c7327b96
Create Date: 2024-10-09 15:37:46.744638

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '11675e102ac4'
down_revision = '1118c7327b96'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('file_reference',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('hash', sa.String(), nullable=True),
    sa.Column('minio_path', sa.String(), nullable=True),
    sa.Column('bucket', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
    sa.Column('content_type', sa.String(), nullable=True),
    sa.Column('original_file_name', sa.String(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('meta_data', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'hash', 'file_size_bytes', name='unique_file_reference'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_file_reference_created_by'), 'file_reference', ['created_by'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_file_reference_hash'), 'file_reference', ['hash'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_file_reference_organization_id'), 'file_reference', ['organization_id'], unique=False, schema='cognition')
    op.create_table('file_extraction',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('file_reference_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('extraction_key', sa.String(), nullable=True),
    sa.Column('minio_path', sa.String(), nullable=True),
    sa.Column('bucket', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['file_reference_id'], ['cognition.file_reference.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'file_reference_id', 'extraction_key', name='unique_file_extraction'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_file_extraction_created_by'), 'file_extraction', ['created_by'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_file_extraction_file_reference_id'), 'file_extraction', ['file_reference_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_file_extraction_organization_id'), 'file_extraction', ['organization_id'], unique=False, schema='cognition')
    op.create_table('file_transformation',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('file_extraction_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('transformation_key', sa.String(), nullable=True),
    sa.Column('minio_path', sa.String(), nullable=True),
    sa.Column('bucket', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['file_extraction_id'], ['cognition.file_extraction.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'file_extraction_id', 'transformation_key', name='unique_file_transformation'),
    schema='cognition'
    )
    op.create_index(op.f('ix_cognition_file_transformation_created_by'), 'file_transformation', ['created_by'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_file_transformation_file_extraction_id'), 'file_transformation', ['file_extraction_id'], unique=False, schema='cognition')
    op.create_index(op.f('ix_cognition_file_transformation_organization_id'), 'file_transformation', ['organization_id'], unique=False, schema='cognition')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_cognition_file_transformation_organization_id'), table_name='file_transformation', schema='cognition')
    op.drop_index(op.f('ix_cognition_file_transformation_file_extraction_id'), table_name='file_transformation', schema='cognition')
    op.drop_index(op.f('ix_cognition_file_transformation_created_by'), table_name='file_transformation', schema='cognition')
    op.drop_table('file_transformation', schema='cognition')
    op.drop_index(op.f('ix_cognition_file_extraction_organization_id'), table_name='file_extraction', schema='cognition')
    op.drop_index(op.f('ix_cognition_file_extraction_file_reference_id'), table_name='file_extraction', schema='cognition')
    op.drop_index(op.f('ix_cognition_file_extraction_created_by'), table_name='file_extraction', schema='cognition')
    op.drop_table('file_extraction', schema='cognition')
    op.drop_index(op.f('ix_cognition_file_reference_organization_id'), table_name='file_reference', schema='cognition')
    op.drop_index(op.f('ix_cognition_file_reference_hash'), table_name='file_reference', schema='cognition')
    op.drop_index(op.f('ix_cognition_file_reference_created_by'), table_name='file_reference', schema='cognition')
    op.drop_table('file_reference', schema='cognition')
    # ### end Alembic commands ###
