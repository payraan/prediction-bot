"""
FastAPI Backend
API اصلی برای Mini App - نسخه کامل
"""

import hashlib
import hmac
import json
from urllib.parse import parse_qsl
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select

from src.core.config import get_settings
from src.database.connection import async_session
from src.database.models import Round, Bet, RoundStatus, BetStatus
from src.core.services.user_service import get_or_create_user, get_user_balance
from src.core.services.betting_service import place_bet, get_user_bets
from src.core.services.round_manager import get_betting_open_round, get_active_or_locked_round
from src.core.services.deposit_address_service import get_or_create_deposit_address
from src.core.services.deposit_service import create_deposit_request, get_pending_deposit
from src.core.services.withdrawal_service import request_withdrawal, get_user_withdrawals, WithdrawalError
from src.core.config import settings, SUPPORTED_ASSET_NETWORKS
from src.core.services.price_service import get_current_price
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.core.services.reconciliation import reconcile
from src.core.services.alerts import alert_admin

settings = get_settings()

from src.api.admin import router as admin_router

from src.api.leaderboard import router as leaderboard_router

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from src.api.rate_limit import limiter

app = FastAPI(title="TON Prediction API", version="2.0.0")

# Rate Limiting
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        {"detail": "Rate limit exceeded. Please try again later."},
        status_code=429
    )

# CORS برای Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin Routes
app.include_router(admin_router)
app.include_router(leaderboard_router)

# Scheduler for background jobs
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_jobs():
    """Start background jobs"""
    
    async def daily_reconciliation():
        """Daily reconciliation check"""
        try:
            async with async_session() as session:
                result = await reconcile(session)
                
            # Send daily summary
            if result["status"] == "ok":
                await alert_admin(
                    f"📊 Daily Reconciliation (OK)\n"
                    f"├ User Balance: {result['total_user_balance']} TON\n"
                    f"└ House Fees: {result['total_house_fees']} TON"
                )
        except Exception as e:
            await alert_admin(f"🚨 Reconciliation Error: {e}")
    
    # Run daily at 00:00 UTC
    scheduler.add_job(daily_reconciliation, "cron", hour=0, minute=0)
    scheduler.start()


# === Pydantic Models ===

class UserResponse(BaseModel):
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    balance_available: float
    balance_locked: float


class BalanceItemResponse(BaseModel):
    asset: str
    network: str
    available: float
    locked: float


class RoundResponse(BaseModel):
    id: str
    round_number: int
    asset_symbol: str
    status: str
    total_up: float
    total_down: float
    betting_end_at: str
    seconds_remaining: int
    lock_price: Optional[float]
    settle_price: Optional[float]
    ui_state: str = "BETTING_OPEN"
    message_fa: str = ""

class BetRequest(BaseModel):
    round_id: str
    direction: str
    amount: float


class BetResponse(BaseModel):
    success: bool
    message: str
    bet_id: Optional[str] = None


class BetHistoryItem(BaseModel):
    id: str
    round_number: int
    direction: str
    amount: float
    status: str
    payout: Optional[float]
    created_at: str


class DepositRequest(BaseModel):
    amount: Optional[float] = None
    asset: Optional[str] = None
    network: Optional[str] = None


class DepositResponse(BaseModel):
    memo: str
    to_address: str
    asset: Optional[str] = None
    expected_amount: Optional[float]
    expires_at: str

class WithdrawalRequest(BaseModel):
    amount: float
    to_address: str
    asset: Optional[str] = None
    network: Optional[str] = None


class WithdrawalResponse(BaseModel):
    id: str
    amount: float
    to_address: str
    asset: Optional[str] = None
    status: str
    created_at: str


class WithdrawalHistoryItem(BaseModel):
    id: str
    amount: float
    to_address: str
    asset: Optional[str] = None
    status: str
    tx_hash: Optional[str]
    created_at: str

class PriceResponse(BaseModel):
    symbol: str
    price: float
    timestamp: str


# === Telegram Auth ===

def verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """اعتبارسنجی initData از تلگرام"""
    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        
        if "hash" not in parsed_data:
            return None
            
        received_hash = parsed_data.pop("hash")
        
        data_check_arr = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
        data_check_string = "\n".join(data_check_arr)
        
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash != received_hash:
            return None
            
        if "user" in parsed_data:
            return json.loads(parsed_data["user"])
        return None
        
    except Exception as e:
        print(f"Auth error: {e}")
        return None


async def get_current_user(x_telegram_init_data: str = Header(None)) -> dict:
    """گرفتن کاربر فعلی از initData"""
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing init data")
    
    user_data = verify_telegram_init_data(
        x_telegram_init_data, 
        settings.telegram_bot_token
    )
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid init data")
    
    return user_data


# === Health & Info ===

@app.get("/")
async def root():
    return {"status": "ok", "message": "TON Prediction API v2"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# === User Endpoints ===

@app.get("/api/user/me", response_model=UserResponse)
async def get_me(user_data: dict = Depends(get_current_user)):
    """گرفتن اطلاعات کاربر فعلی"""
    async with async_session() as session:
        db_user = await get_or_create_user(
            session=session,
            telegram_id=user_data["id"],
            username=user_data.get("username"),
            first_name=user_data.get("first_name")
        )
        
        balance = await get_user_balance(session, user_data["id"])
        
        return UserResponse(
            telegram_id=user_data["id"],
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            balance_available=float(balance.available) if balance else 0,
            balance_locked=float(balance.locked) if balance else 0
        )


@app.get("/api/user/balances", response_model=list[BalanceItemResponse])
async def get_user_balances_endpoint(user_data: dict = Depends(get_current_user)):
    """لیست همه بالانس‌های کاربر (Multi-Asset/Multi-Network)"""
    async with async_session() as session:
        # Ensure user exists
        db_user = await get_or_create_user(
            session=session,
            telegram_id=user_data["id"],
            username=user_data.get("username"),
            first_name=user_data.get("first_name")
        )

        from sqlalchemy import select
        from src.database.models import Balance

        rows = (await session.execute(
            select(Balance).where(Balance.user_id == db_user.id)
        )).scalars().all()

        return [
            BalanceItemResponse(
                asset=(r.asset or r.currency or "TON"),
                network=(r.network or "TON"),
                available=float(r.available or 0),
                locked=float(r.locked or 0),
            )
            for r in rows
        ]



# === Round Endpoints ===

@app.get("/api/round/active", response_model=Optional[RoundResponse])
async def get_active_round():
    """گرفتن راند فعال یا LOCKED"""
    async with async_session() as session:
        round_obj = await get_active_or_locked_round(session, "BTCUSDT")
        
        if not round_obj:
            return None
        
        now = datetime.utcnow()

        if round_obj.status == RoundStatus.BETTING_OPEN:
            seconds_remaining = max(0, int((round_obj.betting_end_at - now).total_seconds()))

        elif round_obj.status == RoundStatus.LOCKED:
            lock_time = round_obj.locked_at or now
            settle_delay = settings.round_duration_seconds
            seconds_remaining = max(0, int(settle_delay - (now - lock_time).total_seconds()))

        else:
            seconds_remaining = 0

        
        if round_obj.status == RoundStatus.BETTING_OPEN:
            ui_state = "BETTING_OPEN"
            message_fa = "شرط‌بندی فعال ✅"
        elif round_obj.status == RoundStatus.LOCKED:
            ui_state = "LOCKED_WAITING_RESULT"
            message_fa = "راند قفل شد ⏳ منتظر نتیجه..."
        else:
            ui_state = "NO_ACTIVE_ROUND"
            message_fa = "در انتظار راند جدید..."
        
        return RoundResponse(
            id=str(round_obj.id),
            round_number=round_obj.round_number,
            asset_symbol=round_obj.asset_symbol,
            status=round_obj.status.value,
            total_up=float(round_obj.total_up_amount),
            total_down=float(round_obj.total_down_amount),
            betting_end_at=round_obj.betting_end_at.isoformat(),
            seconds_remaining=seconds_remaining,
            lock_price=float(round_obj.lock_price) if round_obj.lock_price else None,
            settle_price=float(round_obj.settle_price) if round_obj.settle_price else None,
            ui_state=ui_state,
            message_fa=message_fa,
        )

@app.get("/api/round/{round_id}", response_model=RoundResponse)
async def get_round(round_id: str):
    """گرفتن اطلاعات یک راند"""
    async with async_session() as session:
        result = await session.execute(
            select(Round).where(Round.id == round_id)
        )
        round_obj = result.scalar_one_or_none()
        
        if not round_obj:
            raise HTTPException(status_code=404, detail="Round not found")
        
        now = datetime.utcnow()
        seconds_remaining = max(0, int((round_obj.betting_end_at - now).total_seconds()))
        
        return RoundResponse(
            id=str(round_obj.id),
            round_number=round_obj.round_number,
            asset_symbol=round_obj.asset_symbol,
            status=round_obj.status.value,
            total_up=float(round_obj.total_up_amount),
            total_down=float(round_obj.total_down_amount),
            betting_end_at=round_obj.betting_end_at.isoformat(),
            seconds_remaining=seconds_remaining,
            lock_price=float(round_obj.lock_price) if round_obj.lock_price else None,
            settle_price=float(round_obj.settle_price) if round_obj.settle_price else None,
        )


# === Betting Endpoints ===

@app.post("/api/bet/place", response_model=BetResponse)
@limiter.limit("10/minute")
async def place_bet_endpoint(
    request: Request,
    bet: BetRequest,
    user_data: dict = Depends(get_current_user)
):
    """ثبت شرط جدید"""
    
    direction = bet.direction.upper()
    
    if direction not in ["UP", "DOWN"]:
        raise HTTPException(status_code=400, detail="Invalid direction")
    
    if bet.amount < settings.min_bet_amount:
        raise HTTPException(status_code=400, detail=f"Minimum bet is {settings.min_bet_amount} TON")
    
    if bet.amount > settings.max_bet_amount:
        raise HTTPException(status_code=400, detail=f"Maximum bet is {settings.max_bet_amount} TON")
    
    async with async_session() as session:
        try:
            new_bet = await place_bet(
                session=session,
                telegram_id=user_data["id"],
                round_id=bet.round_id,
                direction=direction,
                amount=Decimal(str(bet.amount))
            )
            
            return BetResponse(
                success=True,
                message=f"شرط {bet.amount} TON روی {'بالا 📈' if direction == 'UP' else 'پایین 📉'} ثبت شد!",
                bet_id=str(new_bet.id)
            )
            
        except ValueError as e:
            return BetResponse(success=False, message=str(e))
        except Exception as e:
            print(f"Bet error: {e}")
            return BetResponse(success=False, message="خطا در ثبت شرط")


@app.get("/api/bet/history", response_model=List[BetHistoryItem])
async def get_bet_history(user_data: dict = Depends(get_current_user), limit: int = 20):
    """تاریخچه شرط‌های کاربر"""
    async with async_session() as session:
        bets = await get_user_bets(session, user_data["id"], limit=limit)
        
        result = []
        for bet in bets:
            round_result = await session.execute(
                select(Round.round_number).where(Round.id == bet.round_id)
            )
            round_number = round_result.scalar_one_or_none() or 0
            
            result.append(BetHistoryItem(
                id=str(bet.id),
                round_number=round_number,
                direction=bet.direction.value,
                amount=float(bet.amount),
                status=bet.status.value,
                payout=float(bet.payout) if bet.payout else None,
                created_at=bet.created_at.isoformat()
            ))
        
        return result


def resolve_asset_network_or_400(asset: Optional[str], network: Optional[str]) -> tuple[str, str]:
    a = (asset or (settings.default_asset or "TON")).strip().upper()
    supported = SUPPORTED_ASSET_NETWORKS.get(a)

    if supported is None:
        raise HTTPException(status_code=400, detail=f"دارایی پشتیبانی نمی‌شود: {a}")

    if network is None:
        n = (settings.default_network or "").strip().upper()
    else:
        n = network.strip().upper()

    if n not in supported:
        raise HTTPException(status_code=400, detail=f"شبکه {n} برای دارایی {a} مجاز نیست")

    return a, n

def resolve_network_or_400(
    asset: str,
    network: Optional[str],
) -> str:
    a = asset.strip().upper()
    n = (network or "").strip().upper()

    supported = SUPPORTED_ASSET_NETWORKS.get(a)
    if not supported:
        raise HTTPException(
            status_code=400,
            detail=f"Asset not supported: {a}",
        )

    if n not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Network {n} is not allowed for asset {a}",
        )

    return n

# === Deposit Endpoints ===

@app.post("/api/deposit/request", response_model=DepositResponse)
@limiter.limit("3/hour")
async def request_deposit(
    request: Request,
    deposit: DepositRequest,
    user_data: dict = Depends(get_current_user)
):
    """درخواست واریز جدید"""
    async with async_session() as session:
        pending = await get_pending_deposit(session, user_data["id"])
        
        if pending:
            return DepositResponse(
                memo=pending["memo"],
                to_address=pending["to_address"],
                expected_amount=pending["expected_amount"],
                expires_at=pending["expires_at"]
            )
        
        asset, network = resolve_asset_network_or_400(deposit.asset, deposit.network)

        # USDT/TRC20: address-based deposit (no memo)
        if asset == "USDT" and network == "TRC20":
            # Telegram WebApp initData user payload uses numeric telegram id in user_data["id"]
            try:
                tg_id = int(user_data["id"])
            except Exception:
                raise HTTPException(status_code=500, detail="Missing telegram user id in auth payload")

            da = await get_or_create_deposit_address(
                session=session,
                telegram_id=tg_id,
                asset="USDT",
                network="TRC20",
            )
            return DepositResponse(
                memo=None,
                to_address=da.address,
                expected_amount=None,
                expires_at=None,
            )

        # TON/Legacy (memo-based)
        result = await create_deposit_request(

            session=session,
            telegram_id=user_data["id"],
            expected_amount=Decimal(str(deposit.amount)) if deposit.amount else None,
            expires_minutes=30,
            network=network
        )
        
        return DepositResponse(
            memo=result["memo"],
            to_address=result["to_address"],
            expected_amount=result["expected_amount"],
            expires_at=result["expires_at"]
        )


@app.get("/api/deposit/pending", response_model=Optional[DepositResponse])
async def get_pending_deposit_endpoint(user_data: dict = Depends(get_current_user)):
    """گرفتن درخواست واریز فعال"""
    async with async_session() as session:
        pending = await get_pending_deposit(session, user_data["id"])
        
        if not pending:
            return None
        
        return DepositResponse(
            memo=pending["memo"],
            to_address=pending["to_address"],
            expected_amount=pending["expected_amount"],
            expires_at=pending["expires_at"]
        )

# === Withdrawal Endpoints ===

@app.post("/api/withdrawal/request", response_model=WithdrawalResponse)
@limiter.limit("5/day")
async def request_withdrawal_endpoint(
    request: Request,
    withdrawal: WithdrawalRequest,
    user_data: dict = Depends(get_current_user)
):
    """درخواست برداشت جدید"""
    async with async_session() as session:
        try:
            asset, network = resolve_asset_network_or_400(withdrawal.asset, withdrawal.network)

            w = await request_withdrawal(
                session=session,
                telegram_id=user_data["id"],
                amount=Decimal(str(withdrawal.amount)),
                to_address=withdrawal.to_address
            )
            
            return WithdrawalResponse(
                id=str(w.id),
                amount=float(w.amount),
                to_address=w.to_address,
                status=w.status.value,
                created_at=w.created_at.isoformat()
            )
            
        except WithdrawalError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            print(f"Withdrawal error: {e}")
            raise HTTPException(status_code=500, detail="خطا در ثبت درخواست برداشت")


@app.get("/api/withdrawal/history", response_model=List[WithdrawalHistoryItem])
async def get_withdrawal_history(user_data: dict = Depends(get_current_user), limit: int = 20):
    """تاریخچه برداشت‌های کاربر"""
    async with async_session() as session:
        withdrawals = await get_user_withdrawals(session, user_data["id"], limit=limit)
        
        return [
            WithdrawalHistoryItem(
                id=str(w.id),
                amount=float(w.amount),
                to_address=w.to_address,
                status=w.status.value,
                tx_hash=w.tx_hash,
                created_at=w.created_at.isoformat()
            )
            for w in withdrawals
        ]

# === Price Endpoint ===

@app.get("/api/price/{symbol}", response_model=PriceResponse)
async def get_price(symbol: str = "BTCUSDT"):
    """گرفتن قیمت فعلی"""
    price = await get_current_price(symbol.upper())
    
    if not price:
        raise HTTPException(status_code=503, detail="Price service unavailable")
    
    return PriceResponse(
        symbol=symbol.upper(),
        price=float(price),
        timestamp=datetime.utcnow().isoformat()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
