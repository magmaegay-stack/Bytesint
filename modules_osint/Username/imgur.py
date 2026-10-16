import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

_CLIENT_ID = "546c25a59c58ad7"


def lookup(target):
    clean = target.strip().lstrip("@")
    result = {
        "target": clean,
        "service": "imgur",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }
    try:
        req = urllib.request.Request(
            f"https://api.imgur.com/3/account/{clean}",
            headers={
                "Authorization": f"Client-ID {_CLIENT_ID}",
                "User-Agent": "python-urllib/3.11",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        acc = data.get("data", {})
        created = None
        if acc.get("created"):
            created = datetime.utcfromtimestamp(acc["created"]).strftime("%Y-%m-%d")

        return_data = {
            "username": acc.get("url"),
            "user_id": acc.get("id"),
            "profile_url": f"https://imgur.com/user/{clean}",
            "bio": acc.get("bio"),
            "reputation": acc.get("reputation"),
            "reputation_name": acc.get("reputation_name"),
            "avatar_url": acc.get("avatar"),
            "cover_url": acc.get("cover"),
            "created_at": created,
            "is_blocked": acc.get("is_blocked"),
        }
        result["result"] = "found"
        result["return"] = {
            k: v for k, v in return_data.items()
            if v is not None and v is not False and v != ""
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
        else:
            result["result"] = "error"
            result["return"] = {"error": f"HTTP {e.code}"}
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
