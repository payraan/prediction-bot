"""fix(db): balances unique per user+asset+network

Revision ID: 91841c6cb51b
Revises: 8d35d719095f
Create Date: 2026-02-05 18:55:27.822401

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91841c6cb51b'
down_revision: Union[str, None] = '8d35d719095f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # drop old uniqueness (one balance per user)
    op.drop_constraint("uq_balances_user_id", "balances", type_="unique")

    # new uniqueness (one balance per user+asset+network)
    op.create_unique_constraint(
        "uq_balances_user_asset_network",
        "balances",
        ["user_id", "asset", "network"],
    )



def downgrade() -> None:
    op.drop_constraint("uq_balances_user_asset_network", "balances", type_="unique")
    op.create_unique_constraint("uq_balances_user_id", "balances", ["user_id"])

