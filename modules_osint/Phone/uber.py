import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def uber_lookup(phone: str) -> dict:
    """Uber — phone registration check with account data extraction."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "uber",
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

        # Step 1: load Uber login to get session cookies (includes jwt-session)
        r0 = s.get(
            "https://auth.uber.com/login/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html",
            },
            allow_redirects=True,
            timeout=15,
        )

        # Step 2: POST phone to OTP endpoint with session cookies
        resp = s.post(
            "https://auth.uber.com/v2/phone/otp",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "https://auth.uber.com",
                "Referer": "https://auth.uber.com/login/",
                "x-csrf-token": s.cookies.get("jwt-session", "")[:20],
            },
            json={
                "phone": clean,
                "countryCode": f"+{country_code}",
                "type": "login",
            },
            timeout=20,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            data = {}
            try:
                data = resp.json()
            except Exception:
                data = {}

            account_state = data.get("accountState") or data.get("account_state")
            user_id = data.get("userId") or data.get("user_id") or data.get("uuid")
            name = data.get("name") or data.get("fullName")
            email = data.get("email") or data.get("maskedEmail")
            flow_token = data.get("flowToken") or data.get("flow_token")

            if account_state in ("existing", "EXISTING", "active", "ACTIVE"):
                return_data["registered"] = True
            elif account_state in ("new", "NEW"):
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered", "account_state": "new"}
                return result

            if user_id:
                return_data["account_id"] = user_id
            if name:
                return_data["display_name"] = name
            if email and "@" in str(email):
                return_data["masked_email"] = email
            if account_state:
                return_data["account_state"] = account_state
            if flow_token:
                return_data["flow_token"] = flow_token[:20] + "..."
                if not return_data.get("registered"):
                    return_data["registered"] = True

            return_data["status"] = "otp_requested"
            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v is not None}

        elif resp.status_code == 403:
            # CSRF error — Uber requires proper session flow
            result["result"] = "error"
            result["msg"] = "csrf_required_open_browser"

        elif resp.status_code == 404:
            # Phone not registered
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}

        elif resp.status_code == 429:
            result["result"] = "error"
            result["msg"] = "rate_limited"

        else:
            try:
                data = resp.json()
                err = data.get("message") or data.get("error") or str(data)
                result["result"] = "error"
                result["msg"] = f"HTTP {resp.status_code}: {str(err)[:150]}"
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
    _res = uber_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
