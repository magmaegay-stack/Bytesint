import sys
import json
import re
from curl_cffi import requests


def steam_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    session = requests.Session(impersonate="chrome120")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://store.steampowered.com",
        "Referer": "https://store.steampowered.com/",
        "X-Requested-With": "XMLHttpRequest",
        "X-Prototype-Version": "1.7",
    }

    try:
        # Endpoint Steam per verificare se email è registrata (account recovery)
        resp = session.post(
            "https://store.steampowered.com/join/checkavail/",
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            data={
                "accountname": email.strip(),
                "count": "1",
            },
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

        # bAvailable: true → nome/email disponibile (non registrata)
        # bAvailable: false → già in uso (registrata come username), ma per email non è lo stesso
        available = data.get("bAvailable")
        if available is False:
            result["accountExists"] = True
            return result
        if available is True:
            # Potrebbe essere che non è registrata come username Steam
            # Proviamo con email lookup alternativo
            pass

        # Alternativa: usa il recupero account Steam per email
        resp2 = session.post(
            "https://help.steampowered.com/en/wizard/HelpWithLoginInfo",
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
            data={
                "email": email.strip(),
                "wizard_ajax": "1",
                "s": "4",
            },
            timeout=15,
        )

        status2 = resp2.status_code
        text2 = resp2.text.lower()
        result["raw"]["help_status"] = status2

        not_found = ["no accounts", "couldn't find", "not found", "no steam account", "unable to find"]
        found = ["account found", "accounts found", "we found", "select your account", "account associated"]

        for phrase in not_found:
            if phrase in text2:
                result["accountExists"] = False
                result["raw"]["reason"] = f"phrase: '{phrase}'"
                return result

        for phrase in found:
            if phrase in text2:
                result["accountExists"] = True
                result["raw"]["reason"] = f"phrase: '{phrase}'"
                return result

        return result

    except Exception as e:
        result["raw"] = {"error": str(e)}
        return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = steam_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
