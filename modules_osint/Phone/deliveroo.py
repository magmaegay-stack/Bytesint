import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def deliveroo_lookup(phone: str) -> dict:
    """Deliveroo — phone lookup extracts account data."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "deliveroo",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        s = requests.Session(impersonate="chrome120")

        resp = s.post(
            "https://api.deliveroo.com/orderapp/v1/auth/phone_login",
            headers={
                "User-Agent": "Deliveroo/3.186.0 (iPhone; iOS 16.6; Scale/3.0)",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Language": "en-GB",
                "x-roo-client": "consumer-ios",
                "x-roo-version": "3.186.0",
            },
            json={"phone_number": clean},
            timeout=15,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            data = resp.json()
            user_id = data.get("user_id") or data.get("userId")
            name = data.get("name") or data.get("first_name")
            last = data.get("last_name") or data.get("surname")
            email = data.get("email") or data.get("masked_email")
            token = data.get("session_token") or data.get("token")

            if user_id:
                return_data["account_id"] = user_id
            if name:
                return_data["first_name"] = name
            if last:
                return_data["last_name"] = last
            if email:
                return_data["masked_email"] = email
            if token:
                return_data["session_token"] = token[:16] + "..."

            return_data["registered"] = True
            return_data["status"] = "account_found"
            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v is not None}

        elif resp.status_code == 201:
            # OTP sent
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            existing = data.get("existing_user", data.get("existingUser"))
            return_data["registered"] = bool(existing) if existing is not None else True
            return_data["status"] = "otp_sent"
            for key in ("user_id", "userId", "id"):
                if data.get(key):
                    return_data["account_id"] = data[key]
                    break
            if data.get("email") or data.get("masked_email"):
                return_data["masked_email"] = data.get("email") or data.get("masked_email")
            if data.get("name") or data.get("first_name"):
                return_data["first_name"] = data.get("name") or data.get("first_name")
            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v is not None}

        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}

        elif resp.status_code == 422:
            # Usually unprocessable — can mean "new user" on some flows
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            msg = str(data.get("message") or data.get("error") or "").lower()
            if "new" in msg or "register" in msg or "not found" in msg:
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
            else:
                result["result"] = "error"
                result["msg"] = msg or f"HTTP {resp.status_code}"

        elif resp.status_code == 429:
            result["result"] = "error"
            result["msg"] = "rate_limited"

        else:
            try:
                data = resp.json()
                result["result"] = "error"
                result["msg"] = f"HTTP {resp.status_code}: {str(data)[:150]}"
            except Exception:
                result["result"] = "error"
                result["msg"] = f"HTTP {resp.status_code}"

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = deliveroo_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
