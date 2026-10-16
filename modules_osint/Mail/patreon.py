import sys
import json
import re
from curl_cffi import requests


def patreon_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    session = requests.Session(impersonate="chrome120")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.patreon.com",
        "Referer": "https://www.patreon.com/login",
    }

    try:
        # Patreon ha un endpoint per verificare se un'email è registrata
        # tramite il flow di forgot password
        resp = session.post(
            "https://www.patreon.com/api/auth?include=campaign.null&fields[user]=email",
            headers=headers,
            json={
                "data": {
                    "type": "user",
                    "attributes": {
                        "email": email.strip(),
                        "send_card_statements_to_email": False,
                    },
                }
            },
            timeout=15,
            allow_redirects=True,
        )

        # L'endpoint sopra è per registrazione — se email già esiste ritorna errore
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

        # Errors con "already taken" → email registrata
        errors = data.get("errors", [])
        for err in errors:
            detail = err.get("detail", "").lower()
            title = err.get("title", "").lower()
            if "already" in detail or "taken" in detail or "exists" in detail:
                result["accountExists"] = True
                result["raw"]["reason"] = f"error: '{detail}'"
                return result

        # Prova alternativa: forgot password
        forgot_resp = session.post(
            "https://www.patreon.com/api/auth?include=&fields[user]=",
            headers={
                **headers,
                "Referer": "https://www.patreon.com/passwordreset",
            },
            json={
                "data": {
                    "type": "user",
                    "attributes": {
                        "email": email.strip(),
                    },
                }
            },
            timeout=15,
        )

        # Anche il forgot password potrebbe dare hints
        if forgot_resp.status_code == 200:
            result["accountExists"] = True
            result["raw"]["reason"] = "forgot_password_200"
        elif forgot_resp.status_code == 404:
            result["accountExists"] = False
            result["raw"]["reason"] = "forgot_password_404"

        return result

    except Exception as e:
        result["raw"] = {"error": str(e)}
        return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = patreon_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
