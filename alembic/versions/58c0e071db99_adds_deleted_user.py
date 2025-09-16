"""adds deleted user

Revision ID: 58c0e071db99
Revises: de396670d10f
Create Date: 2025-09-15 14:08:25.901703

"""

from alembic import op
from submodules.model import DELETED_USER_ID, DELETED_USER_EMAIL

# revision identifiers, used by Alembic.
revision = "58c0e071db99"
down_revision = "de396670d10f"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    insert_deleted_user_sql = f"""
insert into	public."user" (
	id,
	organization_id,
	"role",
	last_interaction,
	language_display,
	email,
	verified,
	created_at,
	metadata_public,
	sso_provider,
	use_new_cognition_ui,
	oidc_identifier
) values (
	'{DELETED_USER_ID}', 
	NULL, 
	NULL, 
	NULL, 
	NULL, 
	'{DELETED_USER_EMAIL}', 
	false, 
	NOW(),
	NULL, 
	NULL, 
	false, 
	null
);
"""
    connection.execute(insert_deleted_user_sql)


def downgrade():
    connection = op.get_bind()
    delete_deleted_user_sql = f"""
delete from public."user" where id = '{DELETED_USER_ID}';
"""
    connection.execute(delete_deleted_user_sql)
