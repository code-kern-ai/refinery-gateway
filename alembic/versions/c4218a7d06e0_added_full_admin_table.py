"""Added full admin table

Revision ID: c4218a7d06e0
Revises: 31c4968699ad
Create Date: 2025-04-24 09:12:33.200446

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c4218a7d06e0"
down_revision = "31c4968699ad"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        INSERT INTO global.full_admin_access (id, email, meta_info)
        VALUES
            (gen_random_uuid(), 'l.lumburovska@accompio.com','{}'),
            (gen_random_uuid(), 'j.wittmeyer@accompio.com','{}'),
            (gen_random_uuid(), 'le.schmidt@accompio.com','{}'),
            (gen_random_uuid(), 'a.hrelja@accompio.com','{}'),
            (gen_random_uuid(), 'l.puettmann@accompio.com','{}'),
            (gen_random_uuid(), 'j.hoetter@accompio.com','{}'),
            (gen_random_uuid(), 'h.wenck@accompio.com','{}'),
            (gen_random_uuid(), 'j.wirth@accompio.com','{}')
        """
    )


def downgrade():
    op.execute(
        """
        DELETE FROM global.full_admin_access WHERE email IN (
            'l.lumburovska@accompio.com',
            'j.wittmeyer@accompio.com',
            'le.schmidt@accompio.com',
            'a.hrelja@accompio.com',
            'l.puettmann@accompio.com',
            'j.hoetter@accompio.com',
            'h.wenck@accompio.com',
            'j.wirth@accompio.com'
        )
        """
    )
