import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def revolut_lookup(phone: str) -> dict:
    """Revolut — phone lookup returns @username handle and account info."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "revolut",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        s = requests.Session(impersonate="chrome120")

        # Revolut public user lookup endpoint
        resp = s.get(
            "https://app.revolut.com/api/retail/user/lookup",
            params={"phone": clean},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Origin": "https://app.revolut.com",
                "Referer": "https://app.revolut.com/start",
            },
            timeout=15,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            data = resp.json()

            # Revolut returns: {"phone":"+39...","hasAccount":true,"username":"@john.doe"}
            has_account = data.get("hasAccount", data.get("has_account"))
            username = data.get("username") or data.get("tag")
            user_id = data.get("id") or data.get("userId") or data.get("user_id")
            name = data.get("name") or data.get("fullName") or data.get("full_name")
            avatar = data.get("profile", {}).get("picture") if isinstance(data.get("profile"), dict) else data.get("avatar")

            if has_account or username or user_id:
                return_data["registered"] = True
                if username:
                    return_data["username"] = username
                if user_id:
                    return_data["account_id"] = user_id
                if name:
                    return_data["display_name"] = name
                if avatar:
                    return_data["avatar_url"] = avatar
                return_data["status"] = "account_found"
                result["result"] = "found"
            elif has_account is False:
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
            else:
                # Return whatever we got
                return_data.update({k: v for k, v in data.items() if v is not None and k != "phone"})
                result["result"] = "found"

            result["return"] = {k: v for k, v in return_data.items() if v is not None}

        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}
        elif resp.status_code == 422:
            result["result"] = "not_found"
            result["return"] = {"status": "invalid_phone"}
        elif resp.status_code == 429:
            result["result"] = "error"
            result["msg"] = "rate_limited"
        else:
            # try alternative endpoint
            resp2 = s.post(
                "https://app.revolut.com/api/retail/user/check",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"phone": clean},
                timeout=15,
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                username = data2.get("username") or data2.get("tag")
                if username:
                    return_data["registered"] = True
                    return_data["username"] = username
                    result["result"] = "found"
                    result["return"] = return_data
                else:
                    result["result"] = "error"
                    result["msg"] = f"HTTP {resp.status_code}"
            else:
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
    _res = revolut_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
