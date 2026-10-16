import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def netflix_lookup(phone: str) -> dict:
    """Netflix — phone lookup: account existence + masked email."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "netflix",
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
        s = requests.Session()

        # Netflix forgot-password via phone
        resp = s.post(
            "https://www.netflix.com/login/password-reset-phone-request",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": "https://www.netflix.com/login",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.netflix.com",
            },
            data={
                "phoneNumber": national,
                "countryCode": country_code,
                "phoneCountryCode": f"+{country_code}",
                "flow": "sms",
            },
            timeout=20,
            verify=False,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {}

            status = str(data.get("status") or data.get("result") or "").lower()
            if status in ("success", "ok", "sent") or data.get("success"):
                email = data.get("email") or data.get("maskedEmail") or data.get("masked_email")
                user_id = data.get("customerId") or data.get("customer_id") or data.get("userId")
                profile_id = data.get("profileId") or data.get("profile_id")
                plan = data.get("plan") or data.get("planName")

                if email and "@" in str(email):
                    return_data["masked_email"] = email
                if user_id:
                    return_data["account_id"] = user_id
                if profile_id:
                    return_data["profile_id"] = profile_id
                if plan:
                    return_data["plan"] = plan

                return_data["registered"] = True
                return_data["status"] = "sms_sent"
                result["result"] = "found"

            elif "not found" in status or "no account" in status or not status:
                # Try phone login flow
                resp2 = s.post(
                    "https://www.netflix.com/api/shakti/mre/loginWithPhone",
                    headers={
                        "User-Agent": "Mozilla/5.0 Chrome/122",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Origin": "https://www.netflix.com",
                    },
                    json={
                        "phoneNumber": national,
                        "countryCallingCode": f"+{country_code}",
                        "flow": "sms",
                    },
                    timeout=15,
                )
                if resp2.status_code == 200:
                    d2 = {}
                    try:
                        d2 = resp2.json()
                    except Exception:
                        pass
                    if d2.get("status") == "success" or d2.get("success"):
                        return_data["registered"] = True
                        return_data["status"] = "otp_sent"
                        if d2.get("email") or d2.get("maskedEmail"):
                            return_data["masked_email"] = d2.get("email") or d2.get("maskedEmail")
                        result["result"] = "found"
                    else:
                        result["result"] = "not_found"
                        result["return"] = {"status": "not_registered"}
                else:
                    result["result"] = "not_found"
                    result["return"] = {"status": "not_registered"}
            else:
                result["result"] = "error"
                result["msg"] = status or f"HTTP {resp.status_code}"
                return result

        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}
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
        msg = str(e)
        if "Resolving timed out" in msg or "SSL" in msg or "ssl" in msg.lower():
            result["result"] = "error"
            result["msg"] = "service_unreachable_network_block"
        else:
            result["result"] = "error"
            result["msg"] = msg

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = netflix_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
