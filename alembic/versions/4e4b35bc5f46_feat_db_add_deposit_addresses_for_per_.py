"""feat(db): add deposit_addresses for per-user deposit wallets

Revision ID: 4e4b35bc5f46
Revises: 7d9f630bd998
Create Date: 2026-02-05 18:40:04.130590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e4b35bc5f46'
down_revision: Union[str, None] = '7d9f630bd998'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
