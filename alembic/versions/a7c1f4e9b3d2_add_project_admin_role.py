"""add ADMIN project role

Revision ID: a7c1f4e9b3d2
Revises: d3f8a1c2b9e4
Create Date: 2026-07-30 08:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c1f4e9b3d2'
down_revision: Union[str, None] = 'd3f8a1c2b9e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE projectrole ADD VALUE IF NOT EXISTS 'ADMIN'")


def downgrade() -> None:
    # Postgres не поддерживает DROP VALUE у enum — пересоздаём тип без ADMIN.
    # Участники с ролью ADMIN (глобальные админы, добавленные в проект)
    # переводятся в OWNER, иначе ALTER COLUMN TYPE упадёт на несовместимом значении.
    op.execute(
        "UPDATE project_members SET role = 'OWNER' WHERE role = 'ADMIN'"
    )
    op.execute("ALTER TYPE projectrole RENAME TO projectrole_old")
    op.execute("CREATE TYPE projectrole AS ENUM ('OWNER', 'MANAGER', 'VIEWER')")
    op.execute(
        "ALTER TABLE project_members "
        "ALTER COLUMN role TYPE projectrole USING role::text::projectrole"
    )
    op.execute("DROP TYPE projectrole_old")
