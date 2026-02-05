"""add is_system_user to users

Revision ID: 209da6699b8d
Revises: 685ba05c295d
Create Date: 2026-02-05 15:17:00.338452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '209da6699b8d'
down_revision: Union[str, None] = '685ba05c295d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_system_user", sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column("users", "is_system_user")
