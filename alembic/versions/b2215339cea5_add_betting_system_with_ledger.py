"""add_betting_system_with_ledger

Revision ID: b2215339cea5
Revises: 418c7083695a
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2215339cea5'
down_revision: Union[str, None] = '418c7083695a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ساخت ENUM های جدید
    betstatus = postgresql.ENUM('PENDING', 'WON', 'LOST', 'REFUNDED', name='betstatus', create_type=False)
    betstatus.create(op.get_bind(), checkfirst=True)
    
    ledgereventtype = postgresql.ENUM(
        'BET_LOCK', 'BET_UNLOCK', 'SETTLE_WIN', 'SETTLE_LOSS', 
        'REFUND', 'HOUSE_FEE', 'DEPOSIT', 'WITHDRAWAL',
        name='ledgereventtype', create_type=False
    )
    ledgereventtype.create(op.get_bind(), checkfirst=True)

    # ساخت جدول ledger
    op.create_table('ledger',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('round_id', sa.UUID(), nullable=True),
        sa.Column('bet_id', sa.UUID(), nullable=True),
        sa.Column('event_type', postgresql.ENUM('BET_LOCK', 'BET_UNLOCK', 'SETTLE_WIN', 'SETTLE_LOSS', 'REFUND', 'HOUSE_FEE', 'DEPOSIT', 'WITHDRAWAL', name='ledgereventtype', create_type=False), nullable=False),
        sa.Column('amount', sa.Numeric(precision=20, scale=9), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('available_before', sa.Numeric(precision=20, scale=9), nullable=True),
        sa.Column('available_after', sa.Numeric(precision=20, scale=9), nullable=True),
        sa.Column('locked_before', sa.Numeric(precision=20, scale=9), nullable=True),
        sa.Column('locked_after', sa.Numeric(precision=20, scale=9), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['bet_id'], ['bets.id'], ),
        sa.ForeignKeyConstraint(['round_id'], ['rounds.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ledger_idempotency_key', 'ledger', ['idempotency_key'], unique=True)

    # تغییرات balances
    op.alter_column('balances', 'available',
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=20, scale=9),
        existing_nullable=True,
        nullable=False)
    op.alter_column('balances', 'locked',
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=20, scale=9),
        existing_nullable=True,
        nullable=False)
    op.alter_column('balances', 'currency',
        existing_type=sa.String(length=10),
        nullable=False)

    # تغییرات bets
    op.add_column('bets', sa.Column('status', postgresql.ENUM('PENDING', 'WON', 'LOST', 'REFUNDED', name='betstatus', create_type=False), nullable=False, server_default='PENDING'))
    op.add_column('bets', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.alter_column('bets', 'amount',
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=20, scale=9),
        existing_nullable=False)
    op.alter_column('bets', 'payout',
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=20, scale=9),
        existing_nullable=True)
    op.create_unique_constraint('uq_bet_user_round', 'bets', ['user_id', 'round_id'])
    op.drop_column('bets', 'is_winner')

    # تغییرات deposit_requests
    op.alter_column('deposit_requests', 'expected_amount',
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=20, scale=9),
        existing_nullable=True)

    # تغییرات rounds
    op.add_column('rounds', sa.Column('asset_symbol', sa.String(length=32), nullable=False, server_default='BTCUSDT'))
    op.add_column('rounds', sa.Column('house_fee', sa.Numeric(precision=20, scale=9), nullable=False, server_default='0'))
    op.add_column('rounds', sa.Column('locked_at', sa.DateTime(), nullable=True))
    op.add_column('rounds', sa.Column('settled_at', sa.DateTime(), nullable=True))
    op.alter_column('rounds', 'status',
        existing_type=postgresql.ENUM('BETTING_OPEN', 'LOCKED', 'RESOLVED_UP', 'RESOLVED_DOWN', 'RESOLVED_TIE', 'VOID', 'CANCELLED', name='roundstatus'),
        nullable=False)
    op.alter_column('rounds', 'total_up_amount',
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=20, scale=9),
        existing_nullable=True,
        nullable=False)
    op.alter_column('rounds', 'total_down_amount',
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=20, scale=9),
        existing_nullable=True,
        nullable=False)
    op.drop_constraint('rounds_round_number_key', 'rounds', type_='unique')
    op.create_index('ix_rounds_asset_symbol', 'rounds', ['asset_symbol'], unique=False)
    op.create_unique_constraint('uq_round_asset_number', 'rounds', ['asset_symbol', 'round_number'])
    op.drop_column('rounds', 'settle_at')

    # تغییرات transactions
    op.alter_column('transactions', 'amount',
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=20, scale=9),
        existing_nullable=False)


def downgrade() -> None:
    # transactions
    op.alter_column('transactions', 'amount',
        existing_type=sa.Numeric(precision=20, scale=9),
        type_=sa.Numeric(precision=20, scale=8),
        existing_nullable=False)

    # rounds
    op.add_column('rounds', sa.Column('settle_at', sa.DateTime(), nullable=True))
    op.drop_constraint('uq_round_asset_number', 'rounds', type_='unique')
    op.drop_index('ix_rounds_asset_symbol', table_name='rounds')
    op.create_unique_constraint('rounds_round_number_key', 'rounds', ['round_number'])
    op.alter_column('rounds', 'total_down_amount',
        existing_type=sa.Numeric(precision=20, scale=9),
        type_=sa.Numeric(precision=20, scale=8),
        nullable=True)
    op.alter_column('rounds', 'total_up_amount',
        existing_type=sa.Numeric(precision=20, scale=9),
        type_=sa.Numeric(precision=20, scale=8),
        nullable=True)
    op.alter_column('rounds', 'status',
        existing_type=postgresql.ENUM('BETTING_OPEN', 'LOCKED', 'RESOLVED_UP', 'RESOLVED_DOWN', 'RESOLVED_TIE', 'VOID', 'CANCELLED', name='roundstatus'),
        nullable=True)
    op.drop_column('rounds', 'settled_at')
    op.drop_column('rounds', 'locked_at')
    op.drop_column('rounds', 'house_fee')
    op.drop_column('rounds', 'asset_symbol')

    # deposit_requests
    op.alter_column('deposit_requests', 'expected_amount',
        existing_type=sa.Numeric(precision=20, scale=9),
        type_=sa.Numeric(precision=20, scale=8),
        existing_nullable=True)

    # bets
    op.add_column('bets', sa.Column('is_winner', sa.Boolean(), nullable=True))
    op.drop_constraint('uq_bet_user_round', 'bets', type_='unique')
    op.alter_column('bets', 'payout',
        existing_type=sa.Numeric(precision=20, scale=9),
        type_=sa.Numeric(precision=20, scale=8),
        existing_nullable=True)
    op.alter_column('bets', 'amount',
        existing_type=sa.Numeric(precision=20, scale=9),
        type_=sa.Numeric(precision=20, scale=8),
        existing_nullable=False)
    op.drop_column('bets', 'updated_at')
    op.drop_column('bets', 'status')

    # balances
    op.alter_column('balances', 'currency',
        existing_type=sa.String(length=10),
        nullable=True)
    op.alter_column('balances', 'locked',
        existing_type=sa.Numeric(precision=20, scale=9),
        type_=sa.Numeric(precision=20, scale=8),
        nullable=True)
    op.alter_column('balances', 'available',
        existing_type=sa.Numeric(precision=20, scale=9),
        type_=sa.Numeric(precision=20, scale=8),
        nullable=True)

    # ledger
    op.drop_index('ix_ledger_idempotency_key', table_name='ledger')
    op.drop_table('ledger')
    
    # drop enums
    postgresql.ENUM(name='ledgereventtype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='betstatus').drop(op.get_bind(), checkfirst=True)
