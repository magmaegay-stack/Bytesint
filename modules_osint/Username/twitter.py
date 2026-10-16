import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def twitter_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "twitter",
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
            f"https://x.com/{clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=20,
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

        if "This account doesn't exist" in html or "account doesn't exist" in html:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "username": clean,
            "profile_url": f"https://x.com/{clean}",
            "profile_url_twitter": f"https://twitter.com/{clean}",
            "status": "verified_active",
        }

        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if og_title:
            title = og_title.group(1)
            # Strip "(@handle) on X" / "| Twitter" / "/ X" suffixes
            title = re.sub(r'\s*\(@[^)]+\)', '', title)
            title = re.sub(r'\s*[/|]\s*(X|Twitter)$', '', title, flags=re.IGNORECASE)
            title = re.sub(r'\s+on\s+(X|Twitter)$', '', title, flags=re.IGNORECASE)
            return_data["display_name"] = title.strip()

        og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        if og_desc:
            return_data["bio"] = og_desc.group(1)[:300]

        og_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og_img:
            return_data["avatar_url"] = og_img.group(1)

        # try to extract user data from Next.js __NEXT_DATA__
        next_m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(\{.+?\})</script>', html, re.DOTALL)
        if next_m:
            try:
                nd = json.loads(next_m.group(1))
                user_result = (
                    nd.get("props", {}).get("pageProps", {}).get("timeline", {}).get("profile_user")
                    or nd.get("props", {}).get("pageProps", {}).get("user")
                )
                if user_result:
                    legacy = user_result.get("legacy", user_result)
                    return_data.update({
                        "display_name": legacy.get("name") or return_data.get("display_name"),
                        "bio": legacy.get("description") or return_data.get("bio"),
                        "followers": legacy.get("followers_count"),
                        "following": legacy.get("friends_count"),
                        "tweets": legacy.get("statuses_count"),
                        "is_verified": legacy.get("verified", False),
                        "location": legacy.get("location") or None,
                        "website": legacy.get("url") or None,
                    })
                    if legacy.get("created_at"):
                        return_data["joined"] = legacy["created_at"]
            except Exception:
                pass

        if "display_name" in return_data or "bio" in return_data:
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
    _res = twitter_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
