import sys
import json
from curl_cffi import requests

def shein_lookup(email: str) -> dict:
    result = {
        "accountExists": False,
        "raw": None,
    }

    # Usiamo una sessione con impersonazione mobile (es. Android Chrome o client specifico)
    session = requests.Session(impersonate="chrome110")

    # Endpoint alternativo mobile/gateway o headers ottimizzati
    url = "https://www.shein.com/gateway-api/v1/identity/account/check"

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "it-IT,it;q=0.9",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://m.shein.com",
        "Referer": "https://m.shein.com/",
        "x-requested-with": "XMLHttpRequest"
    }

    try:
        # Passiamo prima dalla versione mobile per raccogliere eventuali cookie validi
        session.get("https://m.shein.com/", timeout=15)

        payload = {
            "email": email.strip()
        }

        response = session.post(
            url,
            headers=headers,
            json=payload,
            timeout=15,
        )

        text_content = response.text
        
        try:
            raw = response.json()
            result["raw"] = raw
            if raw.get("code") == 0 or raw.get("success") == True or "exist" in str(raw).lower():
                result["accountExists"] = True
        except Exception:
            result["raw"] = {"text_response": text_content[:300] if text_content else "Risposta vuota"}

        return result

    except Exception as e:
        result["raw"] = {"error": str(e)}
        return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = shein_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
