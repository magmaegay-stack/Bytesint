import json
import uuid
from typing import Any, Dict
from curl_cffi import requests


def deliveroo(email: str) -> Dict[str, Any]:
    # Usiamo curl_cffi con impersonazione browser per evitare i blocchi anti-bot
    session = requests.Session(impersonate="chrome")

    result = {
        "exists": None,
        "rate_limited": False,
        "raw": None,
    }

    try:
        session.get(
            "https://deliveroo.co.uk/",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=15,
        )
    except Exception as e:
        result["rate_limited"] = True
        result["raw"] = {"error": str(e)}
        return result

    guid = str(uuid.uuid4())

    headers = {
        "Accept": "application/json, application/vnd.api+json",
        "Content-Type": "application/json",
        "Origin": "https://deliveroo.co.uk",
        "Referer": "https://deliveroo.co.uk/",
        "X-Roo-Client": "consumer-web-app",
        "X-Roo-Client-Referer": "https://deliveroo.co.uk/",
        "X-Roo-Country": "uk",
        "X-Roo-Guid": guid,
        "X-Roo-Platform": "web",
        "X-Roo-Session-Guid": str(uuid.uuid4()),
        "X-Roo-Sticky-Guid": guid,
    }

    payload = {
        "email_address": email,
        "redirect_path": "/",
        "page_in_progress": "login",
    }

    try:
        r = session.post(
            "https://api.uk.deliveroo.com/consumer/accounts/check-email",
            headers=headers,
            json=payload,
            timeout=15,
        )
    except Exception as e:
        result["rate_limited"] = True
        result["raw"] = {"error": str(e)}
        return result

    try:
        data = r.json()
    except Exception:
        result["rate_limited"] = True
        # Stampiamo il testo grezzo per debug se fallisce ancora
        result["raw"] = {"error": "json_parse_failed", "response_text": r.text[:200]}
        return result

    result["raw"] = data

    if "registered" in data:
        result["exists"] = bool(data["registered"])
    else:
        result["rate_limited"] = True

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = deliveroo(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
