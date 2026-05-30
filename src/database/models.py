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
    CheckConstraint, UniqueConstraint, func
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
    
    balances = relationship("Balance", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    bets = relationship("Bet", back_populates="user")
    ledger_entries = relationship("Ledger", back_populates="user")
    stats = relationship("UserStats", back_populates="user", uselist=False)

    is_system_user = Column(Boolean, nullable=False, default=False)

    @property
    def balance(self):
        """Backward-compat: return the default/legacy balance (prefer TON/Ton)."""
        # Prefer TON balance if present
        for b in getattr(self, "balances", []) or []:
            if (getattr(b, "asset", "").upper() == "TON") and (getattr(b, "network", "").upper() == "TON"):
                return b
        # Else return first balance if any
        bs = getattr(self, "balances", None) or []
        return bs[0] if bs else None


class Balance(Base):
    """مدل موجودی کاربر"""
    __tablename__ = "balances"
    __table_args__ = (
        CheckConstraint('available >= 0', name='check_available_non_negative'),
        CheckConstraint('locked >= 0', name='check_locked_non_negative'),
        UniqueConstraint("user_id", "asset", "network", name="uq_balances_user_asset_network"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    available = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)
    locked = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)
    currency = Column(String(10), default="TON", nullable=False)
    asset = Column(String(10), default="TON", nullable=False)
    network = Column(String(10), default="TON", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="balances")


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
    asset = Column(String(10), default="TON", nullable=False)
    network = Column(String(10), default="TON", nullable=False)
    memo = Column(String(255), unique=True, nullable=False)
    expected_amount = Column(Numeric(20, 9), nullable=True)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # ✅ اینو اضافه کن
    to_address = Column(String(128), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")



class DepositAddress(Base):
    """Per-user deposit address mapping (exchange-style)"""
    __tablename__ = "deposit_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    asset = Column(String(10), nullable=False)
    network = Column(String(10), nullable=False)
    address = Column(String(128), nullable=False)

    derivation_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

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
    asset = Column(String(10), default="TON", nullable=False)
    network = Column(String(10), default="TON", nullable=False)

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

class WithdrawalStatus(str, Enum):
    """وضعیت برداشت"""
    PENDING = "PENDING"           # در انتظار پردازش خودکار
    NEEDS_REVIEW = "NEEDS_REVIEW" # نیاز به تأیید ادمین (مبلغ بالا)
    APPROVED = "APPROVED"         # تأیید شده توسط ادمین
    PROCESSING = "PROCESSING"     # در حال پردازش
    COMPLETED = "COMPLETED"       # تکمیل شده
    FAILED = "FAILED"            # خطا در پردازش
    CANCELLED = "CANCELLED"      # لغو شده

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
    asset = Column(String(10), default="TON", nullable=False)
    network = Column(String(10), default="TON", nullable=False)
    to_address = Column(String(255), nullable=False)
    status = Column(SQLEnum(WithdrawalStatus), default=WithdrawalStatus.PENDING, nullable=False)
    tx_hash = Column(String(255), nullable=True, unique=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    user = relationship("User")

class Asset(str, Enum):
    TON = "TON"
    USDT = "USDT"


class Network(str, Enum):
    TON = "TON"        # legacy
    TRC20 = "TRC20"
    ERC20 = "ERC20"
    BEP20 = "BEP20"


# ============================================================
# NEW HYBRID PREDICTION SYSTEM MODELS
# ============================================================
import uuid
from decimal import Decimal
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Text, Integer, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class MarketType(str, Enum):
    LOCAL = "LOCAL"
    POLYMARKET = "POLYMARKET"

class MarketStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PENDING_RESOLUTION = "PENDING_RESOLUTION"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"

class PredictionDirection(str, Enum):
    YES = "YES"
    NO = "NO"

class PredictionStatus(str, Enum):
    OPEN = "OPEN"
    WON = "WON"
    LOST = "LOST"
    REFUNDED = "REFUNDED"

class PropPhase(str, Enum):
    PHASE1 = "PHASE1"
    PHASE2 = "PHASE2"
    FUNDED = "FUNDED"
    BREACHED = "BREACHED"
    COMPLETED = "COMPLETED"

class PropStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PASSED = "PASSED"
    FAILED = "FAILED"
    PENDING_PAYOUT = "PENDING_PAYOUT"


class Market(Base):
    __tablename__ = "markets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(64), nullable=True)
    
    market_type = Column(SQLEnum(MarketType), nullable=False, default=MarketType.LOCAL)
    status = Column(SQLEnum(MarketStatus), nullable=False, default=MarketStatus.DRAFT)
    
    polymarket_condition_id = Column(String(255), nullable=True, unique=True)
    polymarket_token_id_yes = Column(String(255), nullable=True)
    polymarket_token_id_no = Column(String(255), nullable=True)
    polymarket_end_date = Column(DateTime, nullable=True)
    
    yes_price = Column(Numeric(6, 4), nullable=True)
    no_price = Column(Numeric(6, 4), nullable=True)
    
    total_pool_yes = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)
    total_pool_no = Column(Numeric(20, 9), default=Decimal("0"), nullable=False)
    min_prediction_amount = Column(Numeric(20, 9), default=Decimal("1"), nullable=False)
    max_prediction_amount = Column(Numeric(20, 9), default=Decimal("1000"), nullable=False)
    
    opens_at = Column(DateTime, nullable=True)
    closes_at = Column(DateTime, nullable=False)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_featured = Column(Boolean, default=False)
    eligible_for_prop = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    predictions = relationship("Prediction", back_populates="market")
    resolutions = relationship("MarketResolution", back_populates="market")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "market_id", "account_context",
                        name="uq_prediction_user_market_context"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    
    account_context = Column(String(16), nullable=False, default="real")
    prop_account_id = Column(UUID(as_uuid=True), ForeignKey("prop_accounts.id"), nullable=True)
    
    direction = Column(SQLEnum(PredictionDirection), nullable=False)
    amount = Column(Numeric(20, 9), nullable=False)
    status = Column(SQLEnum(PredictionStatus), default=PredictionStatus.OPEN, nullable=False)
    
    entry_price = Column(Numeric(6, 4), nullable=True)
    exit_price = Column(Numeric(6, 4), nullable=True)
    
    payout = Column(Numeric(20, 9), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User")
    market = relationship("Market", back_populates="predictions")
    prop_account = relationship("PropAccount", back_populates="predictions")


class MarketResolution(Base):
    __tablename__ = "market_resolutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    
    outcome = Column(String(8), nullable=False)
    evidence_url = Column(String(1024), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    admin_note = Column(Text, nullable=True)
    
    proposed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    dispute_deadline = Column(DateTime, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    is_finalized = Column(Boolean, default=False)
    dispute_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    market = relationship("Market", back_populates="resolutions")


class PropAccount(Base):
    __tablename__ = "prop_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    phase = Column(SQLEnum(PropPhase), nullable=False, default=PropPhase.PHASE1)
    status = Column(SQLEnum(PropStatus), nullable=False, default=PropStatus.ACTIVE)
    
    virtual_balance = Column(Numeric(20, 2), nullable=False)
    starting_balance = Column(Numeric(20, 2), nullable=False)
    peak_balance = Column(Numeric(20, 2), nullable=False)
    
    target_profit_pct = Column(Numeric(5, 2), nullable=False)
    max_daily_drawdown_pct = Column(Numeric(5, 2), nullable=False)
    max_total_drawdown_pct = Column(Numeric(5, 2), nullable=False)
    min_predictions = Column(Integer, nullable=False, default=10)
    
    total_predictions = Column(Integer, default=0, nullable=False)
    winning_predictions = Column(Integer, default=0, nullable=False)
    losing_predictions = Column(Integer, default=0, nullable=False)
    
    realized_pnl = Column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    funded_amount = Column(Numeric(20, 2), nullable=True)
    profit_split_pct = Column(Numeric(5, 2), default=Decimal("80"), nullable=False)
    
    challenge_fee = Column(Numeric(20, 9), nullable=True)
    challenge_fee_asset = Column(String(10), nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    passed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    funded_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
    predictions = relationship("Prediction", back_populates="prop_account")


class DemoCredit(Base):
    __tablename__ = "demo_credits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    demo_balance = Column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    monthly_credit = Column(Numeric(20, 2), default=Decimal("100"), nullable=False)
    last_credited_at = Column(DateTime, nullable=True)
    next_credit_at = Column(DateTime, nullable=True)
    total_credited = Column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")



class DailyEquitySnapshot(Base):
    __tablename__ = 'daily_equity_snapshots'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prop_account_id = Column(UUID(as_uuid=True), ForeignKey('prop_accounts.id'))
    date = Column(DateTime, default=datetime.utcnow)
    start_of_day_equity = Column(Numeric(18, 8), nullable=False)
