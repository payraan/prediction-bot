"""fix(db): apply deposit schema (no-op safe)

Revision ID: 15e471012a94
Revises: 7381d585cf7a
Create Date: 2026-02-05 18:49:23.727178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15e471012a94'
down_revision: Union[str, None] = '7381d585cf7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
