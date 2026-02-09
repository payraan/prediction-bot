import os
from typing import Optional
"""
Application Configuration
تنظیمات مرکزی برنامه
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """تنظیمات اصلی برنامه"""
    
    # === Application ===
    debug: bool = Field(default=False, alias="DEBUG")
    
    # === Telegram ===
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    
    # === Database ===
    database_url: str = Field(..., alias="DATABASE_URL")
    
    # === TON Blockchain ===
    ton_house_wallet_address: Optional[str] = Field(default=None, alias="TON_HOUSE_WALLET_ADDRESS")
    ton_network: str = Field(default="testnet", alias="TON_NETWORK")
    # === TRON HD Wallet (for per-user TRC20 deposit addresses) ===
    tron_mnemonic: Optional[str] = Field(default=None, alias="TRON_MNEMONIC")
    evm_mnemonic: Optional[str] = Field(default=None, alias="EVM_MNEMONIC")


    # === USDT House Wallets (per network) ===
    usdt_trc20_house_wallet_address: Optional[str] = Field(default=None, alias="USDT_TRC20_HOUSE_WALLET_ADDRESS")
    usdt_erc20_house_wallet_address: Optional[str] = Field(default=None, alias="USDT_ERC20_HOUSE_WALLET_ADDRESS")
    usdt_bep20_house_wallet_address: Optional[str] = Field(default=None, alias="USDT_BEP20_HOUSE_WALLET_ADDRESS")
    
    # === Mini App ===
    webapp_url: str = Field(default="", alias="WEBAPP_URL")
    
    # === Game Settings ===
    round_duration_seconds: int = Field(default=300, alias="ROUND_DURATION_SECONDS")
    rake_percentage: float = Field(default=4.0, alias="RAKE_PERCENTAGE")
    min_bet_amount: float = Field(default=1.0, alias="MIN_BET_AMOUNT")
    max_bet_amount: float = Field(default=1000.0, alias="MAX_BET_AMOUNT")
    
    # === Settlement Asset/Network (Legacy default) ===
    default_asset: str = Field(default="TON", alias="DEFAULT_ASSET")
    default_network: str = Field(default="TON", alias="DEFAULT_NETWORK")


    # === Admin ===
    admin_secret: str = Field(default="change_me_in_production", alias="ADMIN_SECRET")
    admin_telegram_chat_id: Optional[int] = Field(default=None, alias="ADMIN_TELEGRAM_CHAT_ID")
    
    # === Ghost Bot ===
    ghost_bot_enabled: bool = Field(default=True, alias="GHOST_BOT_ENABLED")
    ghost_bot_telegram_id: int = Field(default=777000, alias="GHOST_BOT_TELEGRAM_ID")
    ghost_bot_min_bet: float = Field(default=1.0, alias="GHOST_BOT_MIN_BET")
    ghost_bot_max_bet: float = Field(default=5.0, alias="GHOST_BOT_MAX_BET")
    ghost_bot_minority_threshold: float = Field(default=0.30, alias="GHOST_BOT_MINORITY_THRESHOLD")
    ghost_bot_max_round_exposure: float = Field(default=0.20, alias="GHOST_BOT_MAX_ROUND_EXPOSURE")
    ghost_bot_min_time_left_seconds: int = Field(default=60, alias="GHOST_BOT_MIN_TIME_LEFT_SECONDS")

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    s = Settings()

    # Sanitize TRON mnemonic: remove common copy/paste artifacts (quotes, leading '=', extra whitespace)
    if s.tron_mnemonic:
        mn = s.tron_mnemonic.strip().strip('"').strip("'")
        if mn.startswith("="):
            mn = mn[1:].strip()
        mn = " ".join(mn.split())
        s.tron_mnemonic = mn

    if s.evm_mnemonic:
        mn = s.evm_mnemonic.strip().strip('"').strip("'")
        if mn.startswith("="):
            mn = mn[1:].strip()
        mn = " ".join(mn.split())
        s.evm_mnemonic = mn

    return s

# Convenience singleton (cached)
settings = get_settings()

# Supported settlement asset/network pairs
SUPPORTED_ASSET_NETWORKS = {
    "TON": {"TON"},

    "USDT": {"TRC20", "ERC20", "BEP20"},
}

def get_house_wallet_address(asset: str, network: str) -> Optional[str]:
    """
    Return house wallet address for given asset/network.
    Keeps TON legacy default, and enables USDT per-network addresses via env.
    """
    a = (asset or "").strip().upper()
    n = (network or "").strip().upper()

    if a == "TON" and n == "TON":
        return settings.ton_house_wallet_address

    if a == "USDT":
        if n == "TRC20":
            return settings.usdt_trc20_house_wallet_address
        if n == "ERC20":
            return settings.usdt_erc20_house_wallet_address
        if n == "BEP20":
            return settings.usdt_bep20_house_wallet_address

    return None


# TRC20 token contracts (mainnet)
TRC20_TOKEN_CONTRACTS = {
    ("USDT", "TRC20"): "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
}

# EVM (ERC20/BEP20) token contracts (mainnet)
EVM_TOKEN_CONTRACTS = {
    ("USDT", "ERC20"): "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # Ethereum mainnet
    ("USDT", "BEP20"): "0x55d398326f99059fF775485246999027B3197955",  # BSC mainnet
}

# EVM RPC endpoints (default public RPCs, override via env)
EVM_RPC_URLS = {
    "ERC20": os.getenv("ERC20_RPC_URL", "https://eth.llamarpc.com"),
    "BEP20": os.getenv("BEP20_RPC_URL", "https://bsc-dataseed1.binance.org"),
}

# EVM required confirmations
EVM_CONFIRMATIONS = {
    "ERC20": int(os.getenv("ERC20_CONFIRMATIONS", "12")),
    "BEP20": int(os.getenv("BEP20_CONFIRMATIONS", "5")),
}
