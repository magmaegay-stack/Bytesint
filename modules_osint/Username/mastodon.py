import json
import os
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def mastodon_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "mastodon",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        resp = requests.get(
            f"https://mastodon.social/api/v1/accounts/lookup?acct={clean}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
            impersonate="chrome120",
            timeout=12,
        )

        if resp.status_code == 200:
            d = resp.json()
            if d.get("id"):
                bio_html = d.get("note", "")
                bio_text = BeautifulSoup(bio_html, "html.parser").get_text(strip=True) if bio_html else ""

                return_data = {
                    "username": d.get("username", clean),
                    "display_name": d.get("display_name") or None,
                    "profile_url": d.get("url"),
                    "status": "verified_active",
                    "id": d.get("id"),
                    "followers": d.get("followers_count", 0),
                    "following": d.get("following_count", 0),
                    "posts": d.get("statuses_count", 0),
                    "avatar_url": d.get("avatar"),
                    "bio": bio_text[:200] or None,
                    "is_bot": d.get("bot", False) or None,
                    "locked": d.get("locked", False) or None,
                    "server": "mastodon.social",
                }

                if d.get("created_at"):
                    return_data["created"] = d["created_at"][:10]

                # extract links from fields
                fields = d.get("fields", [])
                if fields:
                    return_data["links"] = [
                        {"name": f.get("name"), "value": BeautifulSoup(f.get("value", ""), "html.parser").get_text(strip=True)}
                        for f in fields if f.get("name")
                    ]

                result["result"] = "found"
                result["return"] = {k: v for k, v in return_data.items() if v is not None and v != "" and v is not False}

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
    _res = mastodon_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
