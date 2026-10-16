import sys
import json
import re
from curl_cffi import requests


def pinterest_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    session = requests.Session(impersonate="chrome120")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "X-APP-VERSION": "58f07f9",
        "X-Pinterest-AppState": "active",
        "Origin": "https://www.pinterest.com",
        "Referer": "https://www.pinterest.com/",
    }

    try:
        # Ottieni il CSRFToken da pinterest
        page = session.get("https://www.pinterest.com/password/reset/", headers=headers, timeout=15)
        csrf = re.search(r'"csrftoken"\s*:\s*"([^"]+)"', page.text)
        csrf_val = csrf.group(1) if csrf else ""
        if not csrf_val:
            # Prova dal cookie
            for cookie in session.cookies:
                if cookie.name == "csrftoken":
                    csrf_val = cookie.value
                    break

        # Invia richiesta reset password
        resp = session.post(
            "https://www.pinterest.com/resource/UserPasswordResetEmailResource/create/",
            headers={
                **headers,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-CSRFToken": csrf_val,
            },
            data={
                "data": json.dumps({
                    "options": {"email": email.strip()},
                    "context": {},
                }),
                "source_url": "/password/reset/",
                "_": "",
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

        # Pinterest risponde con status nell'oggetto response
        resource_resp = data.get("resource_response", {})
        resp_status = resource_resp.get("status", "")
        resp_message = resource_resp.get("message", "").lower()
        resp_code = resource_resp.get("code", 0)

        if resp_status == "success" or resp_code == 0:
            result["accountExists"] = True
            return result

        # Errore: email non trovata
        if "not found" in resp_message or "no account" in resp_message or resp_code in (16, -1):
            result["accountExists"] = False
            return result

        # Fallback generico
        if status == 200 and not resp_message:
            result["accountExists"] = True
        elif status in (400, 404):
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
    _res = pinterest_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
