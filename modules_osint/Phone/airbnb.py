import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def airbnb_lookup(phone: str) -> dict:
    """Airbnb — phone lookup: account existence + masked email + user ID."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "airbnb",
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

        # Get session cookies (bev) needed for CSRF
        s.get("https://www.airbnb.com/login",
              headers={"User-Agent": "Mozilla/5.0 Chrome/122"}, timeout=15)
        bev = s.cookies.get("bev", "")

        # Airbnb phone OTP endpoint
        resp = s.post(
            "https://www.airbnb.com/api/v2/phone_one_time_passwords",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Airbnb-API-Key": "d306zoyjsyarp7ifhu67rjxn52tv0t20",
                "X-CSRF-Token": bev,
            },
            json={
                "phone_number": clean,
                "operation": "login",
            },
            timeout=20,
        )

        return_data = {"phone": clean}

        def _parse_airbnb(data: dict):
            user_id = (data.get("user_id") or data.get("userId")
                       or data.get("id") or (data.get("user") or {}).get("id"))
            name = ((data.get("user") or {}).get("first_name")
                    or data.get("first_name") or data.get("name"))
            email = ((data.get("user") or {}).get("email")
                     or data.get("email") or data.get("masked_email"))
            avatar = ((data.get("user") or {}).get("picture_url")
                      or data.get("avatar"))
            if user_id:
                return_data["account_id"] = user_id
            if name:
                return_data["first_name"] = name
            if email and "@" in str(email):
                return_data["masked_email"] = email
            if avatar:
                return_data["avatar_url"] = avatar

        if resp.status_code == 200:
            data = resp.json()
            _parse_airbnb(data)
            return_data["registered"] = True
            return_data["status"] = "otp_sent"
            result["result"] = "found"

        elif resp.status_code == 201:
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            _parse_airbnb(data)
            return_data["registered"] = True
            return_data["status"] = "otp_sent"
            result["result"] = "found"

        elif resp.status_code == 400:
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            err_type = str(data.get("error_type") or "").lower()
            err = str(data.get("error_message") or data.get("error") or data.get("message") or "").lower()
            if "not_found" in err_type or "not found" in err or "no account" in err:
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
            elif "unsupported_phone_workflow" in err_type:
                result["result"] = "error"
                result["msg"] = "phone_login_disabled_for_region"
            elif "unsupported_auth_method" in err_type:
                result["result"] = "error"
                result["msg"] = "phone_auth_not_supported"
            else:
                result["result"] = "error"
                result["msg"] = err_type or err or f"HTTP {resp.status_code}"
            return result

        elif resp.status_code == 422:
            result["result"] = "not_found"
            result["return"] = {"status": "invalid_phone"}
            return result

        elif resp.status_code == 429:
            result["result"] = "error"
            result["msg"] = "rate_limited"
            return result

        else:
            # Try web forgot-password flow
            resp2 = s.post(
                "https://www.airbnb.com/api/v2/users/password_reset",
                headers={
                    "User-Agent": "Mozilla/5.0 Chrome/122",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Airbnb-API-Key": "d306zoyjsyarp7ifhu67rjxn52tv0t20",
                },
                json={"email_or_phone": clean},
                timeout=20,
            )
            if resp2.status_code in (200, 201):
                d2 = {}
                try:
                    d2 = resp2.json()
                except Exception:
                    pass
                _parse_airbnb(d2)
                return_data["registered"] = True
                return_data["status"] = "reset_otp_sent"
                result["result"] = "found"
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
    _res = airbnb_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
