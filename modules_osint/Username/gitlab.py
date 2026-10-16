import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def gitlab_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "gitlab",
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
            f"https://gitlab.com/api/v4/users?username={clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
        )

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        users = resp.json()
        if not users:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        user = users[0]

        return_data = {
            "username": user.get("username", clean),
            "profile_url": user.get("web_url", f"https://gitlab.com/{clean}"),
            "status": "verified_active",
            "user_id": user.get("id"),
            "full_name": user.get("name") or None,
            "bio": user.get("bio") or None,
            "location": user.get("location") or None,
            "website": user.get("website_url") or None,
            "organization": user.get("organization") or None,
            "job_title": user.get("job_title") or None,
            "avatar_url": user.get("avatar_url") or None,
            "twitter": user.get("twitter") or None,
            "linkedin": user.get("linkedin") or None,
            "state": user.get("state"),
        }

        if user.get("created_at"):
            return_data["joined"] = user["created_at"][:10]

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
    _res = gitlab_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
