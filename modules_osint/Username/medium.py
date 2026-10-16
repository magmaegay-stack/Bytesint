import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def medium_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "medium",
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
            f"https://medium.com/@{clean}",
            headers=headers,
            impersonate="chrome124",
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

        if "Page not found" in html or "This page doesn't exist" in html:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "username": clean,
            "profile_url": f"https://medium.com/@{clean}",
            "status": "verified_active",
        }

        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if og_title:
            return_data["display_name"] = og_title.group(1).replace("– Medium", "").replace("| Medium", "").strip()

        og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        if og_desc:
            return_data["bio"] = og_desc.group(1)[:300]

        og_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og_img:
            return_data["avatar_url"] = og_img.group(1)

        # followers from JSON embedded
        followers_m = re.search(r'"followerCount"\s*:\s*(\d+)', html)
        if followers_m:
            return_data["followers"] = int(followers_m.group(1))

        # following
        following_m = re.search(r'"followingCount"\s*:\s*(\d+)', html)
        if following_m:
            return_data["following"] = int(following_m.group(1))

        # post count
        posts_m = re.search(r'"userPostsCount"\s*:\s*(\d+)', html)
        if posts_m:
            return_data["posts"] = int(posts_m.group(1))

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
    _res = medium_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
