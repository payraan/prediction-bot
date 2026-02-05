"""fix(db): materialize deposit_addresses and deposit_requests.to_address

Revision ID: 650b1132d125
Revises: bcd07aba72b7
Create Date: 2026-02-05 18:45:06.329884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '650b1132d125'
down_revision: Union[str, None] = 'bcd07aba72b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
