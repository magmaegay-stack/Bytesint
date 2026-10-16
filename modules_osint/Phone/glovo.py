import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def glovo_lookup(phone: str) -> dict:
    """Glovo — check phone registration and extract account data."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "glovo",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        s = requests.Session(impersonate="chrome120")

        headers = {
            "User-Agent": "GlovoApp/7.00.0 (iPhone; iOS 16.0; Scale/3.00)",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Glovo-App-Platform": "IOS",
            "Glovo-App-Version": "7.00.0",
            "Glovo-Location-City-Code": "BCN",
        }

        # Step 1: request OTP — reveals if account exists
        resp = s.post(
            "https://api.glovoapp.com/v3/customers/phone-verification/request",
            headers=headers,
            json={"phone": clean},
            timeout=20,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            data = resp.json()

            # Glovo returns different responses for existing vs new accounts
            verification_id = data.get("verificationId") or data.get("verification_id")
            if verification_id:
                return_data["verification_id"] = verification_id

            account_type = data.get("accountType") or data.get("account_type")
            if account_type:
                return_data["account_type"] = account_type

            # check if account already exists vs new registration
            existing = data.get("existingAccount", data.get("existing_account"))
            if existing is not None:
                return_data["existing_account"] = existing

            # masked email if shown
            masked_email = data.get("email") or data.get("maskedEmail") or data.get("masked_email")
            if masked_email:
                return_data["masked_email"] = masked_email

            # customer_id or user_id if leaked
            for key in ("customerId", "customer_id", "userId", "user_id", "id"):
                if data.get(key):
                    return_data["account_id"] = data[key]
                    break

            return_data["status"] = "otp_requested"
            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v is not None}

        elif resp.status_code == 400:
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            error_code = data.get("errorCode") or data.get("error_code") or data.get("code", "")
            error_msg = str(data.get("message") or data.get("error") or "").lower()

            if "invalid" in error_msg or "not valid" in error_msg:
                result["result"] = "not_found"
                result["return"] = {"status": "invalid_phone"}
            elif error_code:
                result["result"] = "error"
                result["msg"] = f"code:{error_code} {error_msg}"
            else:
                result["result"] = "error"
                result["msg"] = str(data)[:200]

        elif resp.status_code == 422:
            # unprocessable entity — usually phone format issue
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            result["result"] = "not_found"
            result["return"] = {"status": "invalid_phone_format", "raw": str(data)[:100]}

        elif resp.status_code == 429:
            result["result"] = "error"
            result["msg"] = "rate_limited"
        elif resp.status_code == 404:
            result["result"] = "not_found"
            return_data["status"] = "not_registered"
        else:
            # try to parse any data in the response
            try:
                data = resp.json()
                result["result"] = "error"
                result["msg"] = f"HTTP {resp.status_code}: {str(data)[:200]}"
            except Exception:
                result["result"] = "error"
                result["msg"] = f"HTTP {resp.status_code}"

        # Step 2: if we got a verificationId, try the login endpoint for more data
        if return_data.get("verification_id"):
            try:
                resp2 = s.post(
                    "https://api.glovoapp.com/v3/customers/login/phone",
                    headers=headers,
                    json={"phone": clean, "verificationId": return_data["verification_id"]},
                    timeout=10,
                )
                if resp2.status_code == 200:
                    d2 = resp2.json()
                    for key in ("customerId", "customer_id", "userId", "user_id", "id"):
                        if d2.get(key) and not return_data.get("account_id"):
                            return_data["account_id"] = d2[key]
                    if d2.get("email") and not return_data.get("masked_email"):
                        return_data["masked_email"] = d2["email"]
                    if d2.get("firstName") or d2.get("first_name"):
                        return_data["first_name"] = d2.get("firstName") or d2.get("first_name")
                    if d2.get("lastName") or d2.get("last_name"):
                        return_data["last_name"] = d2.get("lastName") or d2.get("last_name")
            except Exception:
                pass

        result["return"] = {k: v for k, v in return_data.items() if v is not None}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = glovo_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
