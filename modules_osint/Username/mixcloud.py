import json
import os
import sys
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from curl_cffi import requests as cffi_requests


def lookup(target):
    clean = target.strip().lstrip("@").strip("/")
    result = {
        "target": clean,
        "service": "mixcloud",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }
    try:
        resp = cffi_requests.get(
            f"https://api.mixcloud.com/{clean}/",
            timeout=15,
        )
        data = resp.json()
        if "error" in data:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        pictures = data.get("pictures") or {}
        return_data = {
            "username": data.get("username"),
            "display_name": data.get("name"),
            "profile_url": data.get("url"),
            "bio": data.get("biog"),
            "city": data.get("city"),
            "country": data.get("country"),
            "follower_count": data.get("follower_count"),
            "following_count": data.get("following_count"),
            "upload_count": data.get("cloudcast_count"),
            "listen_count": data.get("listen_count"),
            "is_verified": data.get("is_verified"),
            "website": data.get("website"),
            "avatar_url": pictures.get("large") or pictures.get("medium"),
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
