import sys
import json
import re
from curl_cffi import requests


def github_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    session = requests.Session(impersonate="chrome120")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://github.com",
        "Referer": "https://github.com/password_reset",
    }

    try:
        # Ottieni token autenticità dalla pagina
        page = session.get("https://github.com/password_reset", headers=headers, timeout=15)
        token_m = re.search(r'name="authenticity_token"[^>]*value="([^"]+)"', page.text)
        token = token_m.group(1) if token_m else ""

        # GitHub forgot password endpoint
        resp = session.post(
            "https://github.com/password_reset",
            headers={
                **headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            data={
                "authenticity_token": token,
                "email": email.strip(),
                "commit": "Send password reset email",
            },
            timeout=15,
            allow_redirects=True,
        )

        status = resp.status_code
        text = resp.text.lower()
        url = resp.url
        result["raw"] = {"status_code": status, "url": url}

        if status == 429:
            result["rate_limited"] = True
            return result

        # GitHub mostra "If there's a GitHub account associated..." (privacy)
        # ma anche errori espliciti
        not_found = [
            "can't find an account with that",
            "couldn't find",
            "no account associated",
            "email address was not found",
        ]
        found = [
            "we'll send a link",
            "reset link sent",
            "we've sent",
            "check your email",
            "email sent",
            "if there's a github account",  # generico ma indica invio
        ]

        for phrase in not_found:
            if phrase in text:
                result["accountExists"] = False
                result["raw"]["reason"] = f"phrase: '{phrase}'"
                return result

        for phrase in found:
            if phrase in text:
                result["accountExists"] = True
                result["raw"]["reason"] = f"phrase: '{phrase}'"
                return result

        # Controlla anche l'API di signup per vedere se l'email è disponibile
        check_resp = session.post(
            "https://github.com/signup_check/email",
            headers={
                **headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            data={
                "authenticity_token": token,
                "value": email.strip(),
            },
            timeout=10,
        )

        check_status = check_resp.status_code
        result["raw"]["check_status"] = check_status

        # 422 Unprocessable Entity → email già in uso (account esiste)
        if check_status == 422:
            result["accountExists"] = True
            result["raw"]["reason"] = "signup_check_422"
        # 200 → email disponibile (non registrata)
        elif check_status == 200:
            try:
                check_data = check_resp.json()
                result["raw"]["check_json"] = check_data
                if check_data.get("errors") or "taken" in str(check_data).lower():
                    result["accountExists"] = True
                else:
                    result["accountExists"] = False
            except Exception:
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
    _res = github_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
