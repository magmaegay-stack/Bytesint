import sys
import json
from curl_cffi import requests


def twitch_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.twitch.tv",
        "Referer": "https://www.twitch.tv/",
        "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
    }

    try:
        # Twitch forgot password endpoint
        resp = requests.post(
            "https://passport.twitch.tv/password_reset_request",
            headers=headers,
            json={"email": email.strip()},
            impersonate="chrome120",
            timeout=15,
        )

        status = resp.status_code
        result["raw"] = {"status_code": status}

        try:
            data = resp.json()
            result["raw"]["json"] = data
        except Exception:
            data = {}
            result["raw"]["text"] = resp.text[:500]

        if status == 429:
            result["rate_limited"] = True
            return result

        # 200 → email trovata, Twitch ha inviato il link
        if status == 200:
            result["accountExists"] = True
            return result

        # 400 / 404 → email non trovata
        error = data.get("error", "").lower()
        message = data.get("message", "").lower()
        code = data.get("error_code", 0)

        not_found_indicators = [
            "not found",
            "no user",
            "invalid",
            "unknown",
        ]
        for ind in not_found_indicators:
            if ind in error or ind in message:
                result["accountExists"] = False
                return result

        # 400 generico → email non registrata
        if status in (400, 404):
            result["accountExists"] = False
        elif status == 200:
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
    _res = twitch_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
