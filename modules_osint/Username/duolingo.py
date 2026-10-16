import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def duolingo_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "duolingo",
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
            f"https://www.duolingo.com/2017-06-30/users?username={clean}&fields=username,name,bio,totalXp,streak,creationDate,courses,followers,following,picture,hasPlus",
            headers=headers,
            impersonate="chrome120",
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
        users = data.get("users", [])

        if not users:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        user = users[0]

        courses = user.get("courses", [])
        learning = [c.get("title", "") for c in courses if c.get("learningLanguage") and c.get("xp", 0) > 0]

        return_data = {
            "username": user.get("username", clean),
            "profile_url": f"https://www.duolingo.com/profile/{clean}",
            "status": "verified_active",
            "name": user.get("name") or None,
            "bio": user.get("bio") or None,
            "total_xp": user.get("totalXp", 0),
            "streak": user.get("streak", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "has_plus": user.get("hasPlus", False),
            "learning_languages": learning if learning else None,
        }

        if user.get("creationDate"):
            from datetime import datetime as dt_
            return_data["joined"] = dt_.utcfromtimestamp(user["creationDate"]).strftime("%Y-%m-%d")

        picture = user.get("picture")
        if picture and "/avatars/" in picture:
            return_data["avatar_url"] = picture.replace("/avatars/", "/avatars/xlarge/")

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
    _res = duolingo_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
