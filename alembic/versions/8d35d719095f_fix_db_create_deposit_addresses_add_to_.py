"""fix(db): create deposit_addresses + add to_address (materialize)

Revision ID: 8d35d719095f
Revises: 5d70f78854a4
Create Date: 2026-02-05 18:50:29.016737

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d35d719095f'
down_revision: Union[str, None] = '5d70f78854a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy.dialects import postgresql

    # 1) deposit_addresses
    op.create_table(
        "deposit_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("asset", sa.String(10), nullable=False),
        sa.Column("network", sa.String(10), nullable=False),
        sa.Column("address", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint(
        "uq_deposit_addresses_user_asset_network",
        "deposit_addresses",
        ["user_id", "asset", "network"],
    )
    op.create_index(
        "ix_deposit_addresses_asset_network_address",
        "deposit_addresses",
        ["asset", "network", "address"],
    )

    # 2) deposit_requests.to_address
    op.add_column("deposit_requests", sa.Column("to_address", sa.String(128), nullable=True))
    op.create_index("ix_deposit_requests_to_address", "deposit_requests", ["to_address"])



def downgrade() -> None:
    # reverse order
    op.drop_index("ix_deposit_requests_to_address", table_name="deposit_requests")
    op.drop_column("deposit_requests", "to_address")

    op.drop_index("ix_deposit_addresses_asset_network_address", table_name="deposit_addresses")
    op.drop_constraint("uq_deposit_addresses_user_asset_network", "deposit_addresses", type_="unique")
    op.drop_table("deposit_addresses")

