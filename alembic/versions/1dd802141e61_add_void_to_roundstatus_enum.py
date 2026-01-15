"""add VOID to roundstatus enum

Revision ID: 1dd802141e61
Revises: 
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1dd802141e61'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # اضافه کردن VOID به enum roundstatus
    op.execute("ALTER TYPE roundstatus ADD VALUE IF NOT EXISTS 'VOID';")


def downgrade() -> None:
    # حذف مقدار از enum در PostgreSQL پیچیده است
    # معمولاً خالی می‌ذاریم یا کامنت می‌زنیم
    pass
