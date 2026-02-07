"""feat(db): add derivation_index to deposit_addresses

Revision ID: 3b17d5f56766
Revises: 91841c6cb51b
Create Date: 2026-02-06 16:37:32.281959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b17d5f56766'
down_revision: Union[str, None] = '91841c6cb51b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add column nullable first (safe for existing rows)
    op.add_column("deposit_addresses", sa.Column("derivation_index", sa.Integer(), nullable=True))

    # 2) Backfill for existing rows deterministically:
    #    For each (asset, network) assign 0..N-1 ordered by created_at, id
    op.execute("""
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY asset, network
                    ORDER BY created_at ASC, id ASC
                ) - 1 AS rn
            FROM deposit_addresses
            WHERE derivation_index IS NULL
        )
        UPDATE deposit_addresses d
        SET derivation_index = ranked.rn
        FROM ranked
        WHERE d.id = ranked.id
    """)

    # 3) Enforce NOT NULL
    op.alter_column("deposit_addresses", "derivation_index", existing_type=sa.Integer(), nullable=False)

    # 4) Unique per (asset, network, derivation_index)
    op.create_unique_constraint(
        "uq_deposit_addresses_asset_network_derivation_index",
        "deposit_addresses",
        ["asset", "network", "derivation_index"],
    )

    # Optional index to speed lookups by (asset, network, derivation_index)
    op.create_index(
        "ix_deposit_addresses_asset_network_derivation_index",
        "deposit_addresses",
        ["asset", "network", "derivation_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_deposit_addresses_asset_network_derivation_index", table_name="deposit_addresses")
    op.drop_constraint("uq_deposit_addresses_asset_network_derivation_index", "deposit_addresses", type_="unique")
    op.drop_column("deposit_addresses", "derivation_index")
