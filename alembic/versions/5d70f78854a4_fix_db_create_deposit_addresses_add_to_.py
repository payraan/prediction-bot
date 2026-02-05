"""fix(db): create deposit_addresses + add to_address (materialize)

Revision ID: 5d70f78854a4
Revises: 15e471012a94
Create Date: 2026-02-05 18:50:14.451071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d70f78854a4'
down_revision: Union[str, None] = '15e471012a94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
