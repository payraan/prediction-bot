"""
Database Models
مدل‌های دیتابیس برای سیستم پیش‌بینی قیمت
نسخه نهایی
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
import uuid

from sqlalchemy import (
    MetaData,
    Column, String, Integer, BigInteger, Numeric,
    DateTime, ForeignKey, Enum as SQLEnum, Boolean, Text,
    CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship



# === Naming Convention for Constraints (Standard) ===
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """کلاس پایه برای همه مدل‌ها"""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)



# === Enums (UPPERCASE to match DB) ===

class TransactionType(str, Enum):
    """فقط برای on-chain transactions"""
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RoundStatus(str, Enum):
    BETTING_OPEN = "BETTING_OPEN"
    LOCKED = "LOCKED"
    RESOLVED_UP = "RESOLVED_UP"
    RESOLVED_DOWN = "RESOLVED_DOWN"
    VOID = "VOID"
    CANCELLED = "CANCELLED"


class BetDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"


class BetStatus(str, Enum):
    PENDING = "PENDING"
    WON = "WON"
    LOST = "LOST"
    REFUNDED = "REFUNDED"


class LedgerEventType(str, Enum):
    """همه حرکت‌های مالی داخلی"""
    BET_LOCK = "BET_LOCK"
    BET_UNLOCK = "BET_UNLOCK"
    SETTLE_WIN = "SETTLE_WIN"
    SETTLE_LOSS = "SETTLE_LOSS"
    REFUND = "REFUND"
    HOUSE_FEE = "HOUSE_FEE"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"

    APPROVED = "APPROVED"         # تأیید شده، در صف ارسال
    SENT = "SENT"                 # ارسال شده به بلاکچین
    CONFIRMED = "CONFIRMED"       # تأیید شده در بلاکچین
    FAILED = "FAILED"             # خطا در ارسال
    CANCELLED = "CANCELLED"       # لغو شده

# === Models ===

class User(Base):
    """مدل کاربر"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)
    
    balance = relationship("Balance", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")
    bets = relationship("Bet", back_populates="user")
    ledger_entries = relationship("Ledger", back_populates="user")
    stats = relationship("UserStats", back_populates="user", uselist=False)

class Balance(Base):
    """مدل موجودی کاربر"""
    __tablename__ = "balances"
    __table_args__ = (
        CheckConstraint('available >= 0', name='check_available_non_negative'),
        CheckConstraint('locked >= 0', name='check_locked_non_negative'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    available = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)
    locked = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)
    currency = Column(String(10), default="TON", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="balance")


class Transaction(Base):
    """مدل تراکنش - فقط برای on-chain"""
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Numeric(20, 9), nullable=False)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    reference_id = Column(String(255), nullable=True)
    tx_hash = Column(String(255), nullable=True, unique=True)
    memo = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="transactions")


class Round(Base):
    """مدل راند بازی - Multi-Asset"""
    __tablename__ = "rounds"
    __table_args__ = (
        UniqueConstraint("asset_symbol", "round_number", name="uq_round_asset_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_number = Column(Integer, nullable=False)
    asset_symbol = Column(String(32), nullable=False, index=True, default="BTCUSDT")
    status = Column(SQLEnum(RoundStatus), default=RoundStatus.BETTING_OPEN, nullable=False)

    lock_price = Column(Numeric(20, 8), nullable=True)
    settle_price = Column(Numeric(20, 8), nullable=True)

    total_up_amount = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)
    total_down_amount = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)
    house_fee = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)

    betting_start_at = Column(DateTime, nullable=False)
    betting_end_at = Column(DateTime, nullable=False)
    locked_at = Column(DateTime, nullable=True)
    settled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    bets = relationship("Bet", back_populates="round")
    ledger_entries = relationship("Ledger", back_populates="round")


class Bet(Base):
    """مدل شرط - یک شرط در هر راند"""
    __tablename__ = "bets"
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_bet_amount_positive'),
        UniqueConstraint("user_id", "round_id", name="uq_bet_user_round"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=False)

    direction = Column(SQLEnum(BetDirection), nullable=False)
    amount = Column(Numeric(20, 9), nullable=False)
    payout = Column(Numeric(20, 9), nullable=True)
    status = Column(SQLEnum(BetStatus), default=BetStatus.PENDING, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="bets")
    round = relationship("Round", back_populates="bets")
    ledger_entries = relationship("Ledger", back_populates="bet")


class DepositRequest(Base):
    """مدل درخواست واریز"""
    __tablename__ = "deposit_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    memo = Column(String(255), unique=True, nullable=False)
    expected_amount = Column(Numeric(20, 9), nullable=True)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")


class Ledger(Base):
    """مدل دفتر کل برای audit"""
    __tablename__ = "ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=True)
    bet_id = Column(UUID(as_uuid=True), ForeignKey("bets.id"), nullable=True)

    event_type = Column(SQLEnum(LedgerEventType), nullable=False)
    amount = Column(Numeric(20, 9), nullable=False)
    currency = Column(String(10), default="TON", nullable=False)

    available_before = Column(Numeric(20, 9), nullable=True)
    available_after = Column(Numeric(20, 9), nullable=True)
    locked_before = Column(Numeric(20, 9), nullable=True)
    locked_after = Column(Numeric(20, 9), nullable=True)

    description = Column(Text, nullable=True)
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="ledger_entries")
    round = relationship("Round", back_populates="ledger_entries")
    bet = relationship("Bet", back_populates="ledger_entries")

class UserStats(Base):
    """User statistics for leaderboard"""
    __tablename__ = "user_stats"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    wins = Column(Integer, default=0, nullable=False)
    losses = Column(Integer, default=0, nullable=False)
    ties = Column(Integer, default=0, nullable=False)
    total_bets = Column(Integer, default=0, nullable=False)
    
    net_pnl = Column(Numeric(18, 8), default=0, nullable=False)
    
    win_streak = Column(Integer, default=0, nullable=False)
    best_streak = Column(Integer, default=0, nullable=False)
    
    score = Column(Numeric(18, 8), default=0, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="stats")

class Withdrawal(Base):
    """مدل درخواست برداشت"""
    __tablename__ = "withdrawals"
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_withdrawal_amount_positive'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(20, 9), nullable=False)
    currency = Column(String(10), default="TON", nullable=False)
    to_address = Column(String(255), nullable=False)
    status = Column(SQLEnum(WithdrawalStatus), default=WithdrawalStatus.PENDING, nullable=False)
    tx_hash = Column(String(255), nullable=True, unique=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    user = relationship("User")
