"""etl api project

Revision ID: cb4412d2ae2e
Revises: eb5ecbee5090
Create Date: 2025-02-11 12:15:10.134446

"""

from alembic import op
import sqlalchemy as sa

import uuid
import datetime


# revision identifiers, used by Alembic.
revision = "cb4412d2ae2e"
down_revision = "eb5ecbee5090"
branch_labels = None
depends_on = None


def upgrade():
    meta = sa.MetaData(op.get_bind())
    meta.reflect(only=("organization", "project"))

    organization = sa.Table("organization", meta)
    project = sa.Table("project", meta)

    org_id, project_id = uuid.UUID(int=0), uuid.UUID(int=0)
    op.bulk_insert(
        organization,
        [
            {
                "id": str(org_id),
                "name": "ETL",
                "started_at": datetime.datetime.now(datetime.timezone.utc),
                "description": "ETL External API",
                "max_rows": 0,
                "max_cols": 0,
                "max_char_count": 0,
                "log_admin_requests": "NO_GET",
                "conversation_lifespan_days": 0,
                "file_lifespan_days": 0,
            }
        ],
    )
    op.bulk_insert(
        project,
        [
            {
                "id": str(project_id),
                "name": "ETL External API",
                "description": "ETL External API Default Project",
                "organization_id": str(org_id),
            }
        ],
    )


def downgrade():
    org_id, project_id = uuid.UUID(int=0), uuid.UUID(int=0)
    op.execute("DELETE FROM \"project\" WHERE id = '{}'".format(str(project_id)))
    op.execute("DELETE FROM \"organization\" WHERE id = '{}'".format(str(org_id)))
