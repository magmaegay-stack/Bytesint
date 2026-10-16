import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def telegram_lookup(phone: str) -> dict:
    """
    Check if a phone number has a Telegram account.
    NOTE: The my.telegram.org web API always accepts any valid phone format and
    sends an SMS (if number is real). We detect invalid formats only.
    For real detection use MTProto (telethon/pyrogram) with a registered account.
    """
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "telegram_phone",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "unknown",
        "return": {},
    }

    phone_digits = clean.lstrip("+")

    # basic format check
    if len(phone_digits) < 7 or len(phone_digits) > 15:
        result["result"] = "not_found"
        result["return"] = {"status": "invalid_format"}
        return result

    try:
        encoded_phone = clean.replace("+", "%2B")
        resp = requests.post(
            "https://my.telegram.org/auth/send_password",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://my.telegram.org",
                "Referer": "https://my.telegram.org/auth",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            },
            data=f"phone={encoded_phone}",
            impersonate="chrome120",
            timeout=15,
        )

        response_text = resp.text.strip()

        if resp.status_code == 200 and "random_hash" in response_text:
            # Telegram accepted the number format — SMS sent if number is real
            # Cannot confirm account exists without receiving the SMS
            result["result"] = "unknown"
            result["return"] = {
                "phone": clean,
                "status": "sms_dispatched_if_registered",
                "note": "Telegram sent verification SMS if number is registered. Cannot confirm without MTProto API.",
            }
        elif "too many tries" in response_text.lower() or "too many" in response_text.lower():
            result["result"] = "error"
            result["msg"] = "rate_limited"
        elif resp.status_code == 200 and ("error" in response_text.lower() or "invalid" in response_text.lower()):
            result["result"] = "not_found"
            result["return"] = {"status": "invalid_number", "raw": response_text[:100]}
        else:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}: {response_text[:100]}"

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = telegram_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
