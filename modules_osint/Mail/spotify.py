import sys
import json
import uuid
from curl_cffi import requests


def spotify_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    installation_id = str(uuid.uuid4())

    payload = {
        "fields": [
            {"field": "FIELD_EMAIL", "value": email.strip()}
        ],
        "client_info": {
            "api_key": "a1e486e2729f46d6bb368d6b2bcda326",
            "app_version": "v2",
            "capabilities": [1],
            "installation_id": installation_id,
            "platform": "www",
            "client_id": "",
        },
        "tracking": {
            "creation_flow": "",
            "creation_point": "https://www.spotify.com/signup/",
            "referrer": "",
            "origin_vertical": "",
            "origin_surface": "",
        },
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/json",
        "Referer": "https://www.spotify.com/",
        "Origin": "https://www.spotify.com",
    }

    try:
        resp = requests.post(
            "https://spclient.wg.spotify.com/signup/public/v2/account/validate",
            headers=headers,
            json=payload,
            impersonate="chrome120",
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

        # Spotify risponde con error.ALREADY_EXISTS se email registrata
        error = data.get("error", {})
        if isinstance(error, dict):
            if "ALREADY_EXISTS" in str(error) or error.get("already_exists"):
                result["accountExists"] = True
                return result
            if error:
                # Ha un errore ma non "già esiste" → email non registrata o altro errore
                result["accountExists"] = False
                return result

        # Risposta vuota / ok senza errori → email disponibile (non registrata)
        if data.get("ok") is not None or status == 200:
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
    _res = spotify_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
