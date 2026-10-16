import sys
import json
from curl_cffi import requests


def stripe_lookup(email: str) -> dict:
    result = {
        "accountExists": False,
        "raw": None,
    }

    session = requests.Session(impersonate="chrome120")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://dashboard.stripe.com",
        "Referer": "https://dashboard.stripe.com/login",
    }

    try:
        # Endpoint forgot-password di Stripe Dashboard
        response = session.post(
            "https://dashboard.stripe.com/ajax/dashboard/forgot_password",
            headers=headers,
            data={"email": email.strip()},
            timeout=15,
        )

        raw_text = response.text[:500]
        result["raw"] = {"status_code": response.status_code, "text": raw_text}

        try:
            data = response.json()
            result["raw"]["json"] = data
            # Stripe restituisce {"success": true} se l'email è registrata e invia una mail di reset
            # restituisce {"error": {...}} o {"success": false} se non trovata
            if data.get("success") is True:
                result["accountExists"] = True
            elif response.status_code == 200 and "success" not in data and "error" not in data:
                result["accountExists"] = True
        except Exception:
            if response.status_code == 200:
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
    _res = stripe_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
