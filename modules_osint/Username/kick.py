import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def kick_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "kick",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        # Kick.com public API
        resp = requests.get(
            f"https://kick.com/api/v2/channels/{clean}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Referer": "https://kick.com/",
            },
            impersonate="chrome120",
            timeout=15,
        )

        if resp.status_code == 200:
            d = resp.json()
            if d.get("id") or d.get("slug"):
                user = d.get("user", {})
                return_data = {
                    "username": d.get("slug", clean),
                    "display_name": user.get("username") or d.get("slug"),
                    "profile_url": f"https://kick.com/{d.get('slug', clean)}",
                    "status": "verified_active",
                    "channel_id": d.get("id"),
                    "bio": d.get("slug_bio") or None,
                    "followers": d.get("followers_count", 0),
                    "is_live": d.get("livestream") is not None,
                    "avatar_url": user.get("profile_pic") or None,
                    "verified": d.get("verified") or False,
                    "playback_url": d.get("playback_url") or None,
                }

                livestream = d.get("livestream")
                if livestream:
                    return_data["live_title"] = livestream.get("session_title")
                    return_data["live_viewers"] = livestream.get("viewer_count", 0)
                    return_data["live_category"] = livestream.get("categories", [{}])[0].get("name") if livestream.get("categories") else None

                result["result"] = "found"
                result["return"] = {k: v for k, v in return_data.items() if v is not None and v is not False and v != 0}

        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
        elif resp.status_code == 429:
            result["result"] = "error"
            result["msg"] = "rate_limited"
        else:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = kick_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
