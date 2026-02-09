"""
Deposit Address Service (Exchange-style)
- Per-user deposit address for (asset, network)
- TRON HD wallet derivation for TRC20 deposits
"""

import uuid
import zlib

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

from src.core.config import get_settings
from src.database.models import User, DepositAddress


settings = get_settings()


class DepositAddressError(Exception):
    pass


def _advisory_keys(asset: str, network: str) -> tuple[int, int]:
    """
    Stable int32 keys for pg_advisory_xact_lock(key1, key2)
    """
    a_u = zlib.crc32(asset.encode("utf-8")) & 0xFFFFFFFF
    n_u = zlib.crc32(network.encode("utf-8")) & 0xFFFFFFFF

    # convert unsigned->signed int32
    a = a_u if a_u < (1 << 31) else a_u - (1 << 32)
    n = n_u if n_u < (1 << 31) else n_u - (1 << 32)
    return a, n


def _derive_tron_address(derivation_index: int) -> str:
    """
    TRON derivation path: m/44'/195'/0'/0/{index}
    """
    mn = (settings.tron_mnemonic or "").strip()
    if not mn:
        raise DepositAddressError("TRON_MNEMONIC is not set")

    wc = len(mn.split())
    if wc not in (12, 24):
        raise DepositAddressError(f"Invalid TRON_MNEMONIC word count: {wc}")

    seed_bytes = Bip39SeedGenerator(mn).Generate()

    ctx = (
        Bip44
        .FromSeed(seed_bytes, Bip44Coins.TRON)
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(int(derivation_index))
    )
    return ctx.PublicKey().ToAddress()


def _derive_evm_address(derivation_index: int) -> str:
    """
    EVM derivation path: m/44'/60'/0'/0/{index}
    Same address works for both ERC20 (Ethereum) and BEP20 (BSC).
    """
    mn = (settings.evm_mnemonic or "").strip()
    if not mn:
        raise DepositAddressError("EVM_MNEMONIC is not set")

    wc = len(mn.split())
    if wc not in (12, 24):
        raise DepositAddressError(f"Invalid EVM_MNEMONIC word count: {wc}")

    seed_bytes = Bip39SeedGenerator(mn).Generate()

    ctx = (
        Bip44
        .FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(int(derivation_index))
    )
    return ctx.PublicKey().ToAddress()


async def _locked_get_or_create(
    session: AsyncSession,
    user: User,
    asset: str,
    network: str,
) -> DepositAddress:
    k1, k2 = _advisory_keys(asset, network)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:k1, :k2)"),
        {"k1": k1, "k2": k2},
    )

    # Re-check
    res = await session.execute(
        select(DepositAddress).where(
            DepositAddress.user_id == user.id,
            DepositAddress.asset == asset,
            DepositAddress.network == network,
        )
    )
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    # Next derivation_index
    res = await session.execute(
        select(func.coalesce(func.max(DepositAddress.derivation_index), -1) + 1).where(
            DepositAddress.asset == asset,
            DepositAddress.network == network,
        )
    )
    next_index = int(res.scalar_one())

    # Route to correct derivation function based on network
    if network == "TRC20":
        address = _derive_tron_address(next_index)
    elif network in ("ERC20", "BEP20"):
        address = _derive_evm_address(next_index)
    else:
        raise DepositAddressError(f"Unsupported network for address derivation: {network}")

    row = DepositAddress(
        id=uuid.uuid4(),
        user_id=user.id,
        asset=asset,
        network=network,
        address=address,
        derivation_index=next_index,
    )
    session.add(row)
    await session.flush()
    return row


async def get_or_create_deposit_address(
    session: AsyncSession,
    telegram_id: int,
    asset: str,
    network: str,
) -> DepositAddress:
    asset = asset.strip().upper()
    network = network.strip().upper()

    res = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = res.scalar_one_or_none()
    if not user:
        raise DepositAddressError("User not found")

    # Fast path
    res = await session.execute(
        select(DepositAddress).where(
            DepositAddress.user_id == user.id,
            DepositAddress.asset == asset,
            DepositAddress.network == network,
        )
    )
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    # Transaction-safe creation
    if session.in_transaction():
        return await _locked_get_or_create(session, user, asset, network)

    async with session.begin():
        return await _locked_get_or_create(session, user, asset, network)
