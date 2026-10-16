import sys
import json
from curl_cffi import requests


def minecraft_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://login.live.com",
        "Referer": "https://login.live.com/",
    }

    try:
        # Minecraft usa Microsoft (Xbox Live) account dal 2021
        # Usiamo l'endpoint Microsoft per verificare se l'email è registrata
        session = requests.Session(impersonate="chrome120")

        # Ottieni credenziali sessione
        init = session.get(
            "https://login.live.com/login.srf?wa=wsignin1.0&rpsnv=13&ct=1&rver=7.0.6737.0&wp=MBI_SSL&wreply=https://account.xbox.com/en-US/accountcreation/createaccount?return_url=%2Fen-US%2F&id=292666",
            headers=headers,
            timeout=15,
        )

        import re
        sFTTag = re.search(r'sFTTag.*?value="([^"]+)"', init.text)
        sCtx = re.search(r'sCtx\s*=\s*"([^"]+)"', init.text)
        flow_token = sFTTag.group(1) if sFTTag else ""

        # Prova con l'endpoint GetCredentialType di Microsoft
        cred_resp = session.post(
            "https://login.live.com/GetCredentialType.srf",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "username": email.strip(),
                "isOtherIdpSupported": True,
                "checkPhones": False,
                "isRemoteNGCSupported": True,
                "isCookieBannerShown": False,
                "isFidoSupported": True,
                "originalRequest": "",
                "country": "US",
                "forceotclogin": False,
                "isExternalFederationDisallowed": False,
                "isRemoteConnectSupported": False,
                "federationFlags": 0,
                "isSignup": False,
                "flowToken": flow_token,
                "isAccessPassSupported": True,
            },
            timeout=15,
        )

        status = cred_resp.status_code
        result["raw"] = {"status_code": status}

        if status == 429:
            result["rate_limited"] = True
            return result

        try:
            data = cred_resp.json()
            result["raw"]["json"] = data
        except Exception:
            data = {}
            result["raw"]["text"] = cred_resp.text[:300]

        # IfExistsResult: 0 = esiste, 1 = non esiste, 5 = altro provider
        if_exists = data.get("IfExistsResult")
        if if_exists == 0:
            result["accountExists"] = True
            result["raw"]["reason"] = "IfExistsResult=0"
        elif if_exists == 1:
            result["accountExists"] = False
            result["raw"]["reason"] = "IfExistsResult=1"
        elif if_exists == 5:
            # Account esiste ma usa provider esterno (Google, ecc.)
            result["accountExists"] = True
            result["raw"]["reason"] = "IfExistsResult=5 (external_provider)"
        elif if_exists is not None:
            result["raw"]["reason"] = f"IfExistsResult={if_exists}"

        return result

    except Exception as e:
        result["raw"] = {"error": str(e)}
        return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = minecraft_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
