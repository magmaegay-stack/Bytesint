import sys
import json
import re
from curl_cffi import requests


def soundcloud_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    session = requests.Session(impersonate="chrome120")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://soundcloud.com",
        "Referer": "https://soundcloud.com/",
    }

    try:
        # SoundCloud forgot password
        resp = session.post(
            "https://api-auth.soundcloud.com/password/reset-request",
            headers=headers,
            json={"identifier": email.strip()},
            timeout=15,
        )

        status = resp.status_code
        result["raw"] = {"status_code": status}

        if status == 429:
            result["rate_limited"] = True
            return result

        try:
            data = resp.json()
            result["raw"]["json"] = data
        except Exception:
            data = {}
            result["raw"]["text"] = resp.text[:300]

        # 200 → email trovata, reset inviato
        if status == 200:
            result["accountExists"] = True
            return result

        # 404 → email non registrata
        if status == 404:
            result["accountExists"] = False
            return result

        # 400 → formato email invalido o non trovata
        msg = str(data).lower()
        if "not found" in msg or "invalid" in msg or "no user" in msg:
            result["accountExists"] = False
        elif "sent" in msg or "email" in msg:
            result["accountExists"] = True

        return result

    except Exception as e:
        result["raw"] = {"error": str(e)}
        return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = soundcloud_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
