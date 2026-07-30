"""drop task rating

Revision ID: d3f8a1c2b9e4
Revises: ab9639854cc6
Create Date: 2026-07-30 07:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f8a1c2b9e4'
down_revision: Union[str, None] = 'ab9639854cc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('rating_1_5', 'tasks', type_='check')
    op.drop_column('tasks', 'rating')


def downgrade() -> None:
    op.add_column('tasks', sa.Column('rating', sa.Integer(), nullable=True))
    op.create_check_constraint('rating_1_5', 'tasks', 'rating between 1 and 5')
