import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def coinbase_lookup(phone: str) -> dict:
    """Coinbase — phone lookup: account existence + masked email."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "coinbase",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    country_code = "1"
    national = clean.lstrip("+")
    try:
        import phonenumbers
        pn = phonenumbers.parse(clean, None)
        country_code = str(pn.country_code)
        national = str(pn.national_number)
    except Exception:
        pass

    try:
        s = requests.Session(impersonate="chrome120")

        # Coinbase — phone number sign-in step
        resp = s.post(
            "https://api.coinbase.com/v2/auth/phone/send_verification_code",
            headers={
                "User-Agent": "CoinbaseMobile/24.12.0.0 (iPhone; iOS 17.0)",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "CB-VERSION": "2024-01-01",
                "CB-CLIENT": "1YusufRMN2Vl8d00",
            },
            json={
                "phone_number": clean,
                "country_calling_code": f"+{country_code}",
            },
            timeout=20,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            data = resp.json()
            # Coinbase may return user context on success
            user_id = (data.get("data", {}).get("id")
                       or data.get("user_id") or data.get("id"))
            email = (data.get("data", {}).get("email")
                     or data.get("email") or data.get("masked_email"))
            name = (data.get("data", {}).get("name")
                    or data.get("name"))
            existing = data.get("existing_user", data.get("existingUser"))

            if user_id:
                return_data["account_id"] = user_id
            if email and "@" in str(email):
                return_data["masked_email"] = email
            if name:
                return_data["display_name"] = name
            if existing is not None:
                return_data["existing_account"] = existing

            return_data["registered"] = True
            return_data["status"] = "sms_sent"
            result["result"] = "found"

        elif resp.status_code == 404:
            # Not registered
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}
            return result

        elif resp.status_code == 400:
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            # Check errors array (Coinbase v2 style)
            errors = data.get("errors", [])
            msg = ""
            for e in errors:
                msg += str(e.get("message") or "").lower()
            msg = msg or str(data.get("message") or "").lower()
            if "not found" in msg or "no account" in msg or "doesn't exist" in msg:
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
            else:
                # Try forgot-password SMS approach
                resp2 = s.post(
                    "https://api.coinbase.com/v2/auth/forgot_password/send_sms",
                    headers={
                        "User-Agent": "CoinbaseMobile/24.12.0.0",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "CB-VERSION": "2024-01-01",
                    },
                    json={"phone": clean},
                    timeout=15,
                )
                if resp2.status_code == 200:
                    d2 = {}
                    try:
                        d2 = resp2.json()
                    except Exception:
                        pass
                    return_data["registered"] = True
                    return_data["status"] = "reset_sms_sent"
                    masked = d2.get("email") or d2.get("masked_email") or (d2.get("data") or {}).get("email")
                    if masked:
                        return_data["masked_email"] = masked
                    result["result"] = "found"
                else:
                    result["result"] = "error"
                    result["msg"] = msg or f"HTTP {resp.status_code}"
            if result["result"] != "found":
                return result

        elif resp.status_code == 422:
            result["result"] = "not_found"
            result["return"] = {"status": "invalid_phone_format"}
            return result

        elif resp.status_code == 429:
            result["result"] = "error"
            result["msg"] = "rate_limited"
            return result

        else:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

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
    _res = coinbase_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
