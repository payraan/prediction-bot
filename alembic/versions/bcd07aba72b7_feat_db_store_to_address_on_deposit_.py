"""feat(db): store to_address on deposit_requests for chain matching

Revision ID: bcd07aba72b7
Revises: 4e4b35bc5f46
Create Date: 2026-02-05 18:40:25.968532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcd07aba72b7'
down_revision: Union[str, None] = '4e4b35bc5f46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
