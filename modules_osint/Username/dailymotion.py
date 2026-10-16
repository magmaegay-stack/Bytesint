import json
import os
import sys
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from curl_cffi import requests as cffi_requests

_FIELDS = "id,screenname,username,description,avatar_720_url,url,created_time,followers_total,videos_total,country"


def lookup(target):
    clean = target.strip().lstrip("@")
    result = {
        "target": clean,
        "service": "dailymotion",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }
    try:
        resp = cffi_requests.get(
            f"https://api.dailymotion.com/user/{clean}?fields={_FIELDS}",
            timeout=15,
        )
        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        data = resp.json()
        if "error" in data:
            result["result"] = "not_found"
            result["return"] = {
                "status": "not_exists",
                "reason": data["error"].get("message"),
            }
            return result

        created = None
        if data.get("created_time"):
            created = datetime.utcfromtimestamp(data["created_time"]).strftime("%Y-%m-%d")

        return_data = {
            "user_id": data.get("id"),
            "username": data.get("username"),
            "display_name": data.get("screenname"),
            "description": data.get("description"),
            "profile_url": data.get("url") or f"https://www.dailymotion.com/{clean}",
            "avatar_url": data.get("avatar_720_url"),
            "country": data.get("country"),
            "created_at": created,
            "followers": data.get("followers_total"),
            "videos": data.get("videos_total"),
        }
        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v is not None}
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
