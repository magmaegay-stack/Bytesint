import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def hackernews_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "hackernews",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        resp = requests.get(
            f"https://hacker-news.firebaseio.com/v0/user/{clean}.json",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
        )

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        data = resp.json()

        if data is None:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "username": data.get("id", clean),
            "profile_url": f"https://news.ycombinator.com/user?id={clean}",
            "status": "verified_active",
            "karma": data.get("karma", 0),
            "delay": data.get("delay", 0),
            "about": data.get("about") or None,
        }

        if data.get("created"):
            from datetime import datetime as dt_
            return_data["joined"] = dt_.utcfromtimestamp(data["created"]).strftime("%Y-%m-%d")

        submitted = data.get("submitted", [])
        if submitted:
            return_data["submissions_count"] = len(submitted)

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v is not None and v != ""}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = hackernews_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
