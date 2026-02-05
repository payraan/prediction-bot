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
    return Settings()

# Convenience singleton (cached)
settings = get_settings()

# Supported settlement asset/network pairs
SUPPORTED_ASSET_NETWORKS = {
    "TON": {"TON"},
    "USDT": {"TRC20", "ERC20", "BEP20"},
}
