import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def steam_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "steam",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.get(
            f"https://steamcommunity.com/id/{clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        html = resp.text

        if "The specified profile could not be found" in html or "Error" in html and "profile" in html.lower():
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        # Check for valid profile by looking for steam ID
        steamid_m = re.search(r'"steamid"\s*:\s*"(\d+)"', html)
        if not steamid_m:
            # also check og:title to verify it's a real profile
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if not og_title or "Steam" not in html:
                result["result"] = "not_found"
                return result

        return_data = {
            "username": clean,
            "profile_url": f"https://steamcommunity.com/id/{clean}",
            "status": "verified_active",
        }

        if steamid_m:
            return_data["steam_id"] = steamid_m.group(1)

        # persona name
        persona_m = re.search(r'"personaname"\s*:\s*"([^"]+)"', html)
        if persona_m:
            return_data["display_name"] = persona_m.group(1)

        # avatar
        avatar_m = re.search(r'"avatarfull"\s*:\s*"([^"]+)"', html)
        if avatar_m:
            return_data["avatar_url"] = avatar_m.group(1)

        # real name from profile page
        realname_m = re.search(r'class="header_real_name ellipsis"[^>]*>\s*<bdi>([^<]+)</bdi>', html)
        if realname_m:
            return_data["real_name"] = realname_m.group(1).strip()

        # location
        location_m = re.search(r'class="header_real_name ellipsis"[^>]*>.*?<img[^>]+>\s*([^<\n]+)', html, re.DOTALL)
        if location_m:
            loc = location_m.group(1).strip()
            if loc and len(loc) < 100:
                return_data["location"] = loc

        # games count
        games_m = re.search(r'(\d+)\s+Games?', html)
        if games_m:
            return_data["games_count"] = int(games_m.group(1))

        # friends
        friends_m = re.search(r'(\d+)\s+[Ff]riend', html)
        if friends_m:
            return_data["friends_count"] = int(friends_m.group(1))

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
    _res = steam_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
