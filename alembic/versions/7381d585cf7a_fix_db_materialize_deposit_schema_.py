"""fix(db): materialize deposit schema objects

Revision ID: 7381d585cf7a
Revises: 7b620ddc742e
Create Date: 2026-02-05 18:47:58.564867

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7381d585cf7a'
down_revision: Union[str, None] = '7b620ddc742e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
