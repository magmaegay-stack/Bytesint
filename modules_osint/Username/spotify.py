import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def spotify_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "spotify",
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
            f"https://open.spotify.com/user/{clean}",
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

        if "not available" in html.lower() and "sorry" in html.lower():
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "username": clean,
            "profile_url": f"https://open.spotify.com/user/{clean}",
            "status": "verified_active",
        }

        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if og_title:
            title = og_title.group(1).replace(" | Spotify", "").strip()
            if title and title.lower() not in ("spotify", ""):
                return_data["display_name"] = title

        og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        if og_desc:
            desc = og_desc.group(1)
            return_data["description"] = desc[:300]
            followers_m = re.search(r'([\d,]+)\s+[Ff]ollower', desc)
            if followers_m:
                return_data["followers"] = followers_m.group(1).replace(",", "")

        og_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og_img and "i.scdn.co" in og_img.group(1):
            return_data["avatar_url"] = og_img.group(1)

        # extract JSON-LD for more data
        jsonld_m = re.search(r'<script type="application/ld\+json">(\{.+?\})</script>', html, re.DOTALL)
        if jsonld_m:
            try:
                ld = json.loads(jsonld_m.group(1))
                if ld.get("name"):
                    return_data["display_name"] = ld["name"]
                if ld.get("interactionStatistic"):
                    for stat in ld["interactionStatistic"]:
                        if "follower" in stat.get("interactionType", "").lower():
                            return_data["followers"] = stat.get("userInteractionCount")
            except Exception:
                pass

        if "display_name" in return_data or "og_title" in return_data:
            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v}
        else:
            result["result"] = "found"
            result["return"] = return_data

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = spotify_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
