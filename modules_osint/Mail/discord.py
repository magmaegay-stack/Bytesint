import sys
import json
from curl_cffi import requests


def discord_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/login",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
    }

    try:
        # Step 1: Prova forgot password — no captcha richiesto
        forgot_resp = requests.post(
            "https://discord.com/api/v9/auth/forgot",
            headers=headers,
            json={"login": email.strip()},
            impersonate="chrome120",
            timeout=15,
        )

        result["raw"] = {"forgot_status": forgot_resp.status_code}

        try:
            forgot_data = forgot_resp.json()
            result["raw"]["forgot_json"] = forgot_data
        except Exception:
            forgot_data = {}

        if forgot_resp.status_code == 429:
            result["rate_limited"] = True
            return result

        # Discord /forgot ritorna sempre 200 {} (privacy protection)
        # Non distingue email esistente da non esistente via questo endpoint.
        # Usiamo il login endpoint come fallback per distinguere i casi.

        # Step 2: Login endpoint per distinguere email valida da non valida
        login_resp = requests.post(
            "https://discord.com/api/v9/auth/login",
            headers=headers,
            json={
                "login": email.strip(),
                "password": "Discord0SINT_xX9!",
                "undelete": False,
                "login_source": None,
                "gift_code_sku_id": None,
            },
            impersonate="chrome120",
            timeout=15,
        )

        status = login_resp.status_code
        result["raw"]["login_status"] = status

        try:
            data = login_resp.json()
            result["raw"]["login_json"] = data
        except Exception:
            data = {}

        if status == 429:
            result["rate_limited"] = True
            return result

        # Captcha → impossibile determinare senza resolver
        captcha_key = data.get("captcha_key")
        if captcha_key or "captcha_required" in str(data):
            result["rate_limited"] = True
            result["raw"]["note"] = "captcha_required"
            return result

        # MFA / token → account trovato, login quasi riuscito
        if data.get("mfa") is True or data.get("token"):
            result["accountExists"] = True
            return result

        errors = data.get("errors", {})
        login_errs = errors.get("login", {}).get("_errors", [])
        password_errs = errors.get("password", {}).get("_errors", [])
        login_codes = [e.get("code", "") for e in login_errs]

        # Errore sul campo "password" → email esiste ma password sbagliata
        if password_errs:
            result["accountExists"] = True
            return result

        # INVALID_LOGIN → email non trovata
        if "INVALID_LOGIN" in login_codes:
            result["accountExists"] = False
            return result

        # Errore generico sul campo "login" → email non trovata
        if login_errs and not password_errs:
            result["accountExists"] = False
            return result

        # Nessun errore specifico con 400 → email esiste
        if status == 400 and not login_errs and not password_errs:
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
    _res = discord_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
