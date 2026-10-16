import json
import os
import sys
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup


def lookup(target):
    clean = target.strip().lstrip("@")
    result = {
        "target": clean,
        "service": "venmo",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }
    try:
        resp = cffi_requests.get(
            f"https://account.venmo.com/u/{clean}",
            impersonate="chrome124",
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")

        if script:
            next_data = json.loads(script.string)
            user = next_data.get("props", {}).get("pageProps", {}).get("user", {})
            return_data = {
                "username": clean,
                "profile_url": f"https://venmo.com/{clean}",
                "display_name": user.get("displayName") or None,
                "first_name": user.get("firstName") or None,
                "last_name": user.get("lastName") or None,
                "user_id": user.get("id") or None,
                "friend_count": user.get("friendCount"),
                "avatar_url": user.get("profilePictureUrl") or None,
                "is_active": user.get("isActive"),
            }
            result["return"] = {
                k: v for k, v in return_data.items()
                if v is not None and v != ""
            }
        else:
            result["return"] = {
                "username": clean,
                "profile_url": f"https://venmo.com/{clean}",
                "status": "verified_active",
            }

        result["result"] = "found"
    except Exception as e:
        result["result"] = "error"
        result["return"] = {"error": str(e)}
    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    print(json.dumps(lookup(_sys.argv[1].strip()), indent=4, ensure_ascii=False))
