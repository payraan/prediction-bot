"""fix(db): actually create deposit_addresses and add to_address

Revision ID: 7b620ddc742e
Revises: 650b1132d125
Create Date: 2026-02-05 18:46:25.228880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b620ddc742e'
down_revision: Union[str, None] = '650b1132d125'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
