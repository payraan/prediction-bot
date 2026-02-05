"""add asset and network columns (multi-network prep)

Revision ID: 7d9f630bd998
Revises: 209da6699b8d
Create Date: 2026-02-05 15:58:54.746191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d9f630bd998'
down_revision: Union[str, None] = '209da6699b8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # balances
    op.add_column("balances", sa.Column("asset", sa.String(length=10), nullable=False, server_default="TON"))
    op.add_column("balances", sa.Column("network", sa.String(length=10), nullable=False, server_default="TON"))

    # ledger
    op.add_column("ledger", sa.Column("asset", sa.String(length=10), nullable=False, server_default="TON"))
    op.add_column("ledger", sa.Column("network", sa.String(length=10), nullable=False, server_default="TON"))

    # withdrawals
    op.add_column("withdrawals", sa.Column("asset", sa.String(length=10), nullable=False, server_default="TON"))
    op.add_column("withdrawals", sa.Column("network", sa.String(length=10), nullable=False, server_default="TON"))

    # deposit_requests
    op.add_column("deposit_requests", sa.Column("asset", sa.String(length=10), nullable=False, server_default="TON"))
    op.add_column("deposit_requests", sa.Column("network", sa.String(length=10), nullable=False, server_default="TON"))



def downgrade() -> None:
    # deposit_requests
    op.drop_column("deposit_requests", "network")
    op.drop_column("deposit_requests", "asset")

    # withdrawals
    op.drop_column("withdrawals", "network")
    op.drop_column("withdrawals", "asset")

    # ledger
    op.drop_column("ledger", "network")
    op.drop_column("ledger", "asset")

    # balances
    op.drop_column("balances", "network")
    op.drop_column("balances", "asset")

