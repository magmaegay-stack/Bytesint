import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def bluesky_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "bluesky",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    # Bluesky handle: username or username.bsky.social
    handle = clean if "." in clean else f"{clean}.bsky.social"

    try:
        resp = requests.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile",
            params={"actor": handle},
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122",
            },
            impersonate="chrome120",
            timeout=12,
        )

        if resp.status_code == 200:
            d = resp.json()
            if d.get("did"):
                return_data = {
                    "username": d.get("handle", handle),
                    "display_name": d.get("displayName") or None,
                    "profile_url": f"https://bsky.app/profile/{d.get('handle', handle)}",
                    "status": "verified_active",
                    "did": d.get("did"),
                    "followers": d.get("followersCount", 0),
                    "following": d.get("followsCount", 0),
                    "posts": d.get("postsCount", 0),
                    "bio": d.get("description", "")[:200] or None,
                    "avatar_url": d.get("avatar"),
                    "banner_url": d.get("banner"),
                    "indexed_at": d.get("indexedAt", "")[:10] or None,
                }

                labels = d.get("labels", [])
                if labels:
                    return_data["labels"] = [l.get("val") for l in labels if l.get("val")]

                result["result"] = "found"
                result["return"] = {k: v for k, v in return_data.items() if v is not None and v != ""}

        elif resp.status_code == 400:
            # profile not found
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
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
    _res = bluesky_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
