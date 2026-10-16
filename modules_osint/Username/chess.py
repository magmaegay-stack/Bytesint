import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def chess_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "chess.com",
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
            f"https://api.chess.com/pub/player/{clean}",
            headers=headers,
            timeout=15,
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        data = resp.json()

        return_data = {
            "username": data.get("username", clean),
            "profile_url": data.get("url", f"https://www.chess.com/member/{clean}"),
            "status": data.get("status", "verified_active"),
            "name": data.get("name") or None,
            "title": data.get("title") or None,
            "country": data.get("country", "").split("/")[-1] if data.get("country") else None,
            "location": data.get("location") or None,
            "followers": data.get("followers", 0),
            "avatar_url": data.get("avatar") or None,
            "is_streamer": data.get("is_streamer", False),
            "twitch_url": data.get("twitch_url") or None,
        }

        if data.get("joined"):
            from datetime import datetime as dt_
            return_data["joined"] = dt_.utcfromtimestamp(data["joined"]).strftime("%Y-%m-%d")
        if data.get("last_online"):
            from datetime import datetime as dt_
            return_data["last_online"] = dt_.utcfromtimestamp(data["last_online"]).strftime("%Y-%m-%d")

        # get stats
        stats_resp = requests.get(
            f"https://api.chess.com/pub/player/{clean}/stats",
            headers=headers,
            impersonate="chrome120",
            timeout=10,
        )
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            ratings = {}
            for mode in ("chess_rapid", "chess_blitz", "chess_bullet", "chess_daily"):
                m_data = stats.get(mode, {})
                last = m_data.get("last", {})
                if last.get("rating"):
                    ratings[mode.replace("chess_", "")] = last["rating"]
            if ratings:
                return_data["ratings"] = ratings

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
    _res = chess_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
