"""add user stats and leaderboard

Revision ID: 685ba05c295d
Revises: a18ceaf6ea91
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '685ba05c295d'
down_revision = 'a18ceaf6ea91'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_stats',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('wins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('losses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ties', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_bets', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('net_pnl', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('win_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('best_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_user_stats_score', 'user_stats', ['score'], postgresql_using='btree')
    op.create_index('ix_user_stats_wins', 'user_stats', ['wins'], postgresql_using='btree')


def downgrade():
    op.drop_index('ix_user_stats_wins', table_name='user_stats')
    op.drop_index('ix_user_stats_score', table_name='user_stats')
    op.drop_table('user_stats')
