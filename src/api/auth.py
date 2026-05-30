import hashlib
import hmac
import json
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException
from src.core.config import settings

def verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """اعتبارسنجی initData از تلگرام"""
    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        if "hash" not in parsed_data:
            return None
        received_hash = parsed_data.pop("hash")
        data_check_arr = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
        data_check_string = "\n".join(data_check_arr)
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
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
    user_data = verify_telegram_init_data(x_telegram_init_data, settings.telegram_bot_token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid init data")
    return user_data
