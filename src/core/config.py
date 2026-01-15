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
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    
    # === Database ===
    database_url: str = Field(..., alias="DATABASE_URL")
    
    # === TON Blockchain ===
    ton_house_wallet_address: str = Field(..., alias="TON_HOUSE_WALLET_ADDRESS")
    ton_network: str = Field(default="testnet", alias="TON_NETWORK")
    
    # === Mini App ===
    webapp_url: str = Field(default="", alias="WEBAPP_URL")
    
    # === Game Settings ===
    round_duration_seconds: int = Field(default=300, alias="ROUND_DURATION_SECONDS")
    rake_percentage: float = Field(default=4.0, alias="RAKE_PERCENTAGE")
    min_bet_amount: float = Field(default=1.0, alias="MIN_BET_AMOUNT")
    max_bet_amount: float = Field(default=1000.0, alias="MAX_BET_AMOUNT")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
