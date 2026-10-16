import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def snapchat_phone_lookup(phone: str) -> dict:
    """Check if a phone number is registered on Snapchat via account recovery flow."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "snapchat_phone",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        s = requests.Session(impersonate="chrome120")

        # Step 1: load the password reset page to get xsrf_token cookie
        _pw_url = "https://accounts.snapchat.com/accounts/password_reset_request"
        r0 = s.get(
            _pw_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=15,
        )

        # Token is in the 'xsrf_token' cookie (confirmed via debugging)
        xsrf_token = s.cookies.get("xsrf_token", "")
        if not xsrf_token:
            m = re.search(r'xsrf[_-]?token[^\"]{0,10}\"([^\"]{8,})', r0.text, re.IGNORECASE)
            if m:
                xsrf_token = m.group(1)

        if not xsrf_token:
            result["result"] = "error"
            result["msg"] = "could_not_get_xsrf_token"
            return result

        # Step 2: submit phone number
        resp = s.post(
            _pw_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://accounts.snapchat.com",
                "Referer": _pw_url,
            },
            data={
                "xsrf_token": xsrf_token,
                "forgot_phone": clean,
            },
            timeout=20,
            allow_redirects=True,
        )

        html = resp.text
        return_data = {"phone": clean}

        # Snapchat is a React SPA — response contains data-message attribute on root div
        # e.g. <div id="reset-password-root" data-message="generic_failure" ...>
        msg_m = re.search(r'data-message=["\']([^"\']+)["\']', html)
        data_msg = msg_m.group(1).strip() if msg_m else ""

        # Positive outcomes (SMS sent)
        if data_msg in ("success", "sms_sent", "sent", "otp_sent", "code_sent"):
            return_data["registered"] = True
            return_data["status"] = "account_found_sms_sent"
            result["result"] = "found"
            result["return"] = return_data

        # Not found / invalid
        elif data_msg in ("account_not_found", "not_found", "invalid_phone",
                          "no_account", "user_not_found"):
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}

        # Generic failure — Snapchat shows this for both invalid and unregistered phones
        elif data_msg == "generic_failure":
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered_or_invalid_phone", "snapchat_msg": data_msg}

        elif resp.status_code in (429, 503) or "too many" in html.lower():
            result["result"] = "error"
            result["msg"] = "rate_limited"

        elif not data_msg:
            result["result"] = "error"
            result["msg"] = "no_data_message_in_response"

        else:
            # Other data-message values — treat as unknown
            result["result"] = "error"
            result["msg"] = f"unknown_data_message: {data_msg}"

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = snapchat_phone_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
