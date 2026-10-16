import json
import sys
import typing
from json import loads
from curl_cffi import requests

def microsoft_recovery(target: str) -> dict[str, typing.Any]:
    result: dict[str, typing.Any] = {
        "accountExists": False,
        "backupEmail": None,
        "phones": [],
        "securityQuestion": None,
        "twoFA": False,
        "raw": [],
    }

    session = requests.Session(impersonate="safari")

    try:
        resp = session.get(
            "https://account.live.com/ResetPassword.aspx",
            params={"mn": target},
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=10,
        )
        

        if '"oProofList":[' not in resp.text:
            return result

        raw = loads(
            f"""[{resp.text.split('"oProofList":[')[1].split("],")[0]}]"""
        )

        result["accountExists"] = True
        result["raw"] = raw

        for item in raw:
            match item.get("type"):
                case "Email":
                    if "*" in item.get("name", ""):
                        result["backupEmail"] = item["name"]
                case "Sms":
                    result["phones"].append(item.get("name"))
                case "SQSA":
                    result["securityQuestion"] = item.get("name")
                case "TOTPAuthenticatorV2":
                    result["twoFA"] = True

    except Exception as e:
        result["error"] = str(e)

    return result

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = microsoft_recovery(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
