import json
import requests
import random
import string
from typing import Dict, Any


def office365(email: str) -> Dict[str, Any]:
    session = requests.Session()

    result = {
        "exists": None,
        "rate_limited": False,
        "raw": None,
    }

    user_agent = "Microsoft Office/16.0 (Windows NT 10.0; Microsoft Outlook 16.0.12026; Pro)"
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }

    def random_digits(length=30):
        return "".join(random.choice(string.digits) for _ in range(length))

    domain = email.split("@", 1)[1]
    fake_email = f"{random_digits()}@{domain}"

    url = (
        "https://outlook.office365.com/"
        "autodiscover/autodiscover.json/v1.0/{}"
        "?Protocol=Autodiscoverv1"
    )

    try:
        r = session.get(
            url.format(fake_email),
            headers=headers,
            allow_redirects=False,
            timeout=15,
        )
        result["raw"] = {
            "backup": r.status_code
        }
    except Exception as e:
        result["rate_limited"] = True
        result["raw"] = {"error": str(e)}
        return result

    if r.status_code != 200:
        try:
            r = session.get(
                url.format(email),
                headers=headers,
                allow_redirects=False,
                timeout=15,
            )
            result["raw"]["status"] = r.status_code
        except Exception as e:
            result["rate_limited"] = True
            result["raw"] = {"error": str(e)}
            return result

        if r.status_code == 200:
            result["exists"] = True
        else:
            result["exists"] = False

    else:
        result["rate_limited"] = True
        result["exists"] = False

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = office365(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
