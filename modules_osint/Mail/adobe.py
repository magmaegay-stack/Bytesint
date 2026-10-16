import random
import sys
import json
from typing import Any, Dict
from curl_cffi import requests

CHROME_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def adobe(email: str) -> Dict[str, Any]:
    result = {
        "accountExists": False,
        "emailRecovery": None,
        "phoneNumber": None,
        "raw": None,
    }

    # Usiamo curl_cffi con impersonazione chrome per bypassare i controlli anti-bot
    session = requests.Session(impersonate="chrome")

    headers = {
        "User-Agent": random.choice(CHROME_UAS),
        "Accept": "application/json, text/plain, */*",
        "X-IMS-CLIENTID": "adobedotcom2",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://auth.services.adobe.com",
        "Referer": "https://auth.services.adobe.com/",
    }

    try:
        r = session.post(
            "https://auth.services.adobe.com/signin/v1/authenticationstate",
            headers=headers,
            json={"username": email, "accountType": "individual"},
            timeout=10,
        )

        try:
            state = r.json()
        except Exception:
            result["raw"] = {"error": "json_parse_failed", "response_text": r.text[:300]}
            return result

        result["raw"] = {"authenticationState": state}

        if "errorCode" in state:
            return result

        # Recuperiamo l'header crittografato per la richiesta successiva
        auth_state_enc = r.headers.get("x-ims-authentication-state-encrypted") or r.headers.get("X-IMS-Authentication-State-Encrypted")
        if auth_state_enc:
            headers["X-IMS-Authentication-State-Encrypted"] = auth_state_enc

        response = session.get(
            "https://auth.services.adobe.com/signin/v2/challenges",
            headers=headers,
            params={"purpose": "passwordRecovery"},
            timeout=10,
        )

        try:
            challenges = response.json()
        except Exception:
            result["raw"]["challenges_error"] = "json_parse_failed"
            return result

        result["raw"]["challenges"] = challenges

        result["accountExists"] = True
        result["emailRecovery"] = challenges.get("secondaryEmail")
        result["phoneNumber"] = challenges.get("securityPhoneNumber")

        return result

    except Exception as e:
        result["raw"] = {"error": str(e)}
        return result

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = adobe(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
