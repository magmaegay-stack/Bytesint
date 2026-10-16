import sys
import json
from curl_cffi import requests


def roblox_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/",
    }

    try:
        # Roblox forgot password endpoint
        resp = requests.post(
            "https://auth.roblox.com/v1/passwords/reset/send",
            headers=headers,
            json={"targetType": "Email", "target": email.strip()},
            impersonate="chrome120",
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

        # 200 → reset email inviata → account esiste
        if status == 200:
            result["accountExists"] = True
            return result

        # 400 → email non trovata o errore
        errors = data.get("errors", [])
        for err in errors:
            code = err.get("code", 0)
            msg = err.get("message", "").lower()
            # Code 5 = "Invalid Email" / non registrata
            # Code 2 = "Flood Check"
            if code == 5 or "invalid" in msg or "not found" in msg:
                result["accountExists"] = False
                return result
            if code == 2:
                result["rate_limited"] = True
                return result

        if status == 400:
            result["accountExists"] = False
        elif status == 403:
            # CSRF token richiesto — proviamo con token
            csrf_resp = requests.get(
                "https://auth.roblox.com/v1/passwords/reset",
                headers=headers,
                impersonate="chrome120",
                timeout=10,
            )
            csrf = csrf_resp.headers.get("x-csrf-token", "")
            if csrf:
                resp2 = requests.post(
                    "https://auth.roblox.com/v1/passwords/reset/send",
                    headers={**headers, "X-CSRF-TOKEN": csrf},
                    json={"targetType": "Email", "target": email.strip()},
                    impersonate="chrome120",
                    timeout=15,
                )
                result["raw"]["csrf_status"] = resp2.status_code
                if resp2.status_code == 200:
                    result["accountExists"] = True
                elif resp2.status_code == 400:
                    result["accountExists"] = False

        return result

    except Exception as e:
        result["raw"] = {"error": str(e)}
        return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = roblox_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
