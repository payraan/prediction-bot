"""
Betting Service
سرویس شرط‌بندی با پشتیبانی از Ledger و Refund
"""

import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.database.models import (
    User, Balance, Round, Bet, Ledger,
    BetStatus, BetDirection, RoundStatus, LedgerEventType
)
from src.core.config import get_settings

from src.core.services.stats_service import apply_bet_result

settings = get_settings()


class BettingError(Exception):
    """خطای شرط‌بندی"""
    pass


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User:
    """گرفتن کاربر با telegram_id"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def place_bet(
    session: AsyncSession,
    telegram_id: int,
    round_id: uuid.UUID,
    direction: str,
    amount: Decimal
) -> Bet:
    """
    ثبت شرط جدید
    ورودی direction می‌تونه "up"/"down" یا "UP"/"DOWN" باشه
    """
    async with session.begin():
        # ۱. گرفتن کاربر
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            raise BettingError("کاربر پیدا نشد. لطفاً اول /start بزنید")

        # ۲. تبدیل direction به enum
        direction_upper = direction.upper()
        if direction_upper == "UP":
            bet_direction = BetDirection.UP
        elif direction_upper == "DOWN":
            bet_direction = BetDirection.DOWN
        else:
            raise BettingError("جهت شرط نامعتبر است")

        # ۳. چک و قفل کردن راند (جلوگیری از Lost Update)
        round_result = await session.execute(
            select(Round).where(Round.id == round_id).with_for_update()
        )
        round_obj = round_result.scalar_one_or_none()

        if not round_obj:
            raise BettingError("راند پیدا نشد")

        if round_obj.status != RoundStatus.BETTING_OPEN:
            raise BettingError("شرط‌بندی برای این راند بسته است")

        if datetime.utcnow() > round_obj.betting_end_at:
            raise BettingError("زمان شرط‌بندی تمام شده")

        # ۴. چک شرط قبلی
        existing_bet = await session.execute(
            select(Bet).where(
                Bet.user_id == user.id,
                Bet.round_id == round_id
            )
        )
        if existing_bet.scalar_one_or_none():
            raise BettingError("شما قبلاً در این راند شرط بسته‌اید")

        # ۵. تعیین دارایی/شبکه + قفل کردن Balance (جلوگیری از Double Spend)
        asset = settings.default_asset.strip().upper()
        network = settings.default_network.strip().upper()

        balance_result = await session.execute(
            select(Balance).where(
                Balance.user_id == user.id,
                Balance.asset == asset,
                Balance.network == network,
            ).with_for_update()
        )
        balance = balance_result.scalar_one_or_none()

        if not balance:
            raise BettingError("موجودی پیدا نشد")

        if balance.available < amount:
            raise BettingError("موجودی کافی نیست")

        # ۶. چک حداقل/حداکثر شرط (همان منطق قبلی)
        min_bet = Decimal(str(settings.min_bet_amount))
        max_bet = Decimal(str(settings.max_bet_amount))

        if amount < min_bet:
            raise BettingError(f"حداقل شرط {min_bet} TON است")

        if amount > max_bet:
            raise BettingError(f"حداکثر شرط {max_bet} TON است")

        # ۷. ذخیره وضعیت قبلی برای Ledger
        available_before = balance.available
        locked_before = balance.locked

        # ۸. انتقال از available به locked
        balance.available -= amount
        balance.locked += amount

        # ۹. ساخت Bet (همان فیلدهای قبلی)
        bet = Bet(
            id=uuid.uuid4(),
            user_id=user.id,
            round_id=round_id,
            direction=bet_direction,
            amount=amount,
            status=BetStatus.PENDING
        )
        session.add(bet)

        # ۱۰. آپدیت مجموع راند
        if bet_direction == BetDirection.UP:
            round_obj.total_up_amount += amount
        else:
            round_obj.total_down_amount += amount

        # ۱۱. ثبت در Ledger
        ledger_entry = Ledger(
            id=uuid.uuid4(),
            user_id=user.id,
            round_id=round_id,
            bet_id=bet.id,
            event_type=LedgerEventType.BET_LOCK,
            amount=amount,
            currency=asset,
            asset=asset,
            network=network,
            available_before=available_before,
            available_after=balance.available,
            locked_before=locked_before,
            locked_after=balance.locked,
            description=f"شرط {amount} {settings.default_asset} روی {bet_direction.value}",
            idempotency_key=f"BET_LOCK:{bet.id}"
        )
        session.add(ledger_entry)

        # flush برای گرفتن خطای constraint قبل از خروج از begin
        try:
            await session.flush()
        except IntegrityError:
            raise BettingError("خطا در ثبت شرط. لطفاً دوباره تلاش کنید")

    return bet


async def settle_round(
    session: AsyncSession,
    round_id: uuid.UUID,
    settle_price: Decimal
) -> dict:
    """
    تسویه راند - idempotent
    """
    async with session.begin():
        # ۱. گرفتن و قفل کردن راند (جلوگیری از تسویه همزمان)
        round_result = await session.execute(
            select(Round).where(Round.id == round_id).with_for_update()
        )
        round_obj = round_result.scalar_one_or_none()

        if not round_obj:
            raise BettingError("راند پیدا نشد")

        # ۲. چک idempotency
        if round_obj.status in [RoundStatus.RESOLVED_UP, RoundStatus.RESOLVED_DOWN, RoundStatus.VOID]:
            return {"status": "already_settled", "round_status": round_obj.status.value}

        if round_obj.status != RoundStatus.LOCKED:
            raise BettingError("راند هنوز قفل نشده")

        asset = settings.default_asset.strip().upper()
        network = settings.default_network.strip().upper()

        # ۳. تعیین نتیجه
        lock_price = round_obj.lock_price

        if settle_price > lock_price:
            winning_direction = BetDirection.UP
            winning_pool = round_obj.total_up_amount
            new_status = RoundStatus.RESOLVED_UP
        elif settle_price < lock_price:
            winning_direction = BetDirection.DOWN
            winning_pool = round_obj.total_down_amount
            new_status = RoundStatus.RESOLVED_DOWN
        else:
            winning_pool = Decimal("0")
            new_status = RoundStatus.VOID

        # ۴. گرفتن همه شرط‌ها
        bets_result = await session.execute(
            select(Bet).where(Bet.round_id == round_id)
        )
        bets = bets_result.scalars().all()

        total_pool = round_obj.total_up_amount + round_obj.total_down_amount
        losing_pool = total_pool - winning_pool

        # ۵. REFUND اگر TIE یا one-sided (هیچ پولی سمت مقابل نیست)
        if losing_pool == Decimal("0") or winning_pool == Decimal("0") or new_status == RoundStatus.VOID:
            return await _refund_all_bets(session, round_obj, bets)

        # ۶. محاسبه کارمزد
        fee_percent = Decimal(str(settings.rake_percentage)) / Decimal("100")
        house_fee = total_pool * fee_percent
        net_pool = total_pool - house_fee
        payout_ratio = net_pool / winning_pool

        round_obj.house_fee = house_fee

        # ثبت کارمزد
        fee_ledger = Ledger(
            id=uuid.uuid4(),
            round_id=round_id,
            event_type=LedgerEventType.HOUSE_FEE,
            amount=house_fee,
            asset=asset,
            network=network,
            description=f"کارمزد {fee_percent*100}%",
            idempotency_key=f"HOUSE_FEE:{round_id}"
        )
        session.add(fee_ledger)

        # ۷. پردازش شرط‌ها
        winners_count = 0
        losers_count = 0

        # مرتب‌سازی برای جلوگیری از Deadlock هنگام قفل کردن Balance
        bets.sort(key=lambda b: str(b.user_id))

        for bet in bets:
            balance_result = await session.execute(
                select(Balance).where(
                    Balance.user_id == bet.user_id,
                    Balance.asset == asset,
                    Balance.network == network,
                ).with_for_update()
            )
            balance = balance_result.scalar_one()

            available_before = balance.available
            locked_before = balance.locked

            if bet.direction == winning_direction:
                payout = bet.amount * payout_ratio
                bet.payout = payout
                bet.status = BetStatus.WON

                balance.locked -= bet.amount
                balance.available += payout

                ledger_entry = Ledger(
                    id=uuid.uuid4(),
                    user_id=bet.user_id,
                    round_id=round_id,
                    bet_id=bet.id,
                    event_type=LedgerEventType.SETTLE_WIN,
                    amount=payout,
                    asset=asset,
                    network=network,
                    available_before=available_before,
                    available_after=balance.available,
                    locked_before=locked_before,
                    locked_after=balance.locked,
                    description=f"برد {payout} {settings.default_asset}",
                    idempotency_key=f"SETTLE_WIN:{round_id}:{bet.id}"
                )
                session.add(ledger_entry)

                pnl = payout - bet.amount
                await apply_bet_result(session, bet.user_id, "WIN", pnl)
                winners_count += 1
            else:
                bet.payout = Decimal("0")
                bet.status = BetStatus.LOST

                balance.locked -= bet.amount

                ledger_entry = Ledger(
                    id=uuid.uuid4(),
                    user_id=bet.user_id,
                    round_id=round_id,
                    bet_id=bet.id,
                    event_type=LedgerEventType.SETTLE_LOSS,
                    amount=bet.amount,
                    asset=asset,
                    network=network,
                    available_before=available_before,
                    available_after=balance.available,
                    locked_before=locked_before,
                    locked_after=balance.locked,
                    description=f"باخت {bet.amount} {settings.default_asset}",
                    idempotency_key=f"SETTLE_LOSS:{round_id}:{bet.id}"
                )
                session.add(ledger_entry)

                await apply_bet_result(session, bet.user_id, "LOSS", -bet.amount)
                losers_count += 1

        # ۸. آپدیت راند
        round_obj.status = new_status
        round_obj.settle_price = settle_price
        round_obj.settled_at = datetime.utcnow()

    return {
        "status": "settled",
        "round_status": new_status.value,
        "winners": winners_count,
        "losers": losers_count,
        "house_fee": float(house_fee),
        "payout_ratio": float(payout_ratio)
    }


async def _refund_all_bets(session: AsyncSession, round_obj: Round, bets: list) -> dict:
    """بازگشت همه شرط‌ها - بدون کارمزد"""

    asset = settings.default_asset.strip().upper()
    network = settings.default_network.strip().upper()

    refunded_count = 0

    # مرتب‌سازی برای جلوگیری از Deadlock
    bets.sort(key=lambda b: str(b.user_id))

    for bet in bets:
        # چک idempotency
        existing = await session.execute(
            select(Ledger).where(Ledger.idempotency_key == f"REFUND:{round_obj.id}:{bet.id}")
        )
        if existing.scalar_one_or_none():
            continue

        # قفل کردن موجودی برای جلوگیری از race با withdraw/place_bet
        balance_result = await session.execute(
            select(Balance).where(
                Balance.user_id == bet.user_id,
                Balance.asset == asset,
                Balance.network == network,
            ).with_for_update()
        )
        balance = balance_result.scalar_one()

        available_before = balance.available
        locked_before = balance.locked

        balance.locked -= bet.amount
        balance.available += bet.amount

        bet.status = BetStatus.REFUNDED
        await apply_bet_result(session, bet.user_id, "TIE", Decimal("0"))
        bet.payout = bet.amount

        ledger_entry = Ledger(
            id=uuid.uuid4(),
            user_id=bet.user_id,
            round_id=round_obj.id,
            bet_id=bet.id,
            event_type=LedgerEventType.REFUND,
            amount=bet.amount,
            available_before=available_before,
            available_after=balance.available,
            locked_before=locked_before,
            locked_after=balance.locked,
            description=f"بازگشت {bet.amount} {asset}",
            idempotency_key=f"REFUND:{round_obj.id}:{bet.id}"
        )
        session.add(ledger_entry)
        refunded_count += 1

    round_obj.status = RoundStatus.VOID
    round_obj.house_fee = Decimal("0")
    round_obj.settled_at = datetime.utcnow()

    return {
        "status": "refunded",
        "round_status": RoundStatus.VOID.value,
        "refunded_count": refunded_count,
        "house_fee": 0
    }


async def get_user_bets(
    session: AsyncSession,
    telegram_id: int,
    limit: int = 20
) -> list:
    """
    گرفتن تاریخچه شرط‌های کاربر
    """
    
    # پیدا کردن کاربر
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if not user:
        return []
    
    # گرفتن شرط‌ها
    result = await session.execute(
        select(Bet)
        .where(Bet.user_id == user.id)
        .order_by(Bet.created_at.desc())
        .limit(limit)
    )
    
    return result.scalars().all()
