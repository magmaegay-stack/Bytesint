import sys
import json
import re
from curl_cffi import requests


def apple_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    IFORGOT = "https://iforgot.apple.com/password/verify/appleid"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://iforgot.apple.com",
        "Referer": "https://iforgot.apple.com/",
    }

    session = requests.Session(impersonate="chrome120")

    try:
        page = session.get(IFORGOT, headers=headers, timeout=20)
        m = re.search(r'"sstt"\s*:\s*"([^"]+)"', page.text)
        if not m:
            result["raw"] = {"error": "sstt_token_not_found"}
            return result

        sstt = m.group(1)

        resp = session.post(
            IFORGOT,
            headers={**headers, "Content-Type": "application/json"},
            json={"id": email.strip(), "sstt": sstt},
            timeout=20,
        )

        status = resp.status_code
        text = resp.text.lower()
        result["raw"] = {"status_code": status, "text_preview": resp.text[:300]}

        if status in (429, 503):
            result["rate_limited"] = True
            return result

        # Non trovato
        if any(x in text for x in ("not found", "doesn't exist", "does not exist", "no account", "-20101", "invalid apple id")):
            result["accountExists"] = False
            return result

        # Trovato: Apple risponde con step successivo del recovery flow
        if any(x in text for x in ("trustedphones", "forgotpassword", "recovery", "verifyphone", "trusted", "phone")):
            if "not found" not in text and "does not exist" not in text:
                result["accountExists"] = True
                return result

        # 200 senza messaggio di errore → account esiste
        if status == 200 and "not found" not in text:
            result["accountExists"] = True
        elif status == 200:
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
    _res = apple_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
