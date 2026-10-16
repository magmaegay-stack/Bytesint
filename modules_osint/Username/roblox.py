import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def roblox_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "roblox",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        user_id = None
        user_name = clean

        # Check if target is a numeric Roblox User ID
        if clean.isdigit():
            user_id = int(clean)
            profile_resp = requests.get(
                f"https://users.roblox.com/v1/users/{user_id}",
                headers=headers,
                impersonate="chrome120",
                timeout=10,
            )
            if profile_resp.status_code == 200:
                p_data = profile_resp.json()
                user_name = p_data.get("name", clean)
                display_name = p_data.get("displayName")
            else:
                user_id = None

        if not user_id:
            # Search by username via users API
            search_resp = requests.post(
                "https://users.roblox.com/v1/usernames/users",
                headers=headers,
                json={"usernames": [clean], "excludeBannedUsers": False},
                impersonate="chrome120",
                timeout=15,
            )

            if search_resp.status_code != 200:
                result["result"] = "error"
                result["msg"] = f"HTTP {search_resp.status_code}"
                return result

            search_data = search_resp.json()
            users = search_data.get("data", [])

            if not users:
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            user = users[0]
            user_id = user.get("id")
            user_name = user.get("name", clean)
            display_name = user.get("displayName")

        return_data = {
            "username": user_name,
            "display_name": display_name or user_name,
            "user_id": user_id,
            "profile_url": f"https://www.roblox.com/users/{user_id}/profile",
            "status": "verified_active",
            "is_banned": False,
        }

        # get full profile
        if user_id:
            profile_resp = requests.get(
                f"https://users.roblox.com/v1/users/{user_id}",
                headers=headers,
                impersonate="chrome120",
                timeout=10,
            )
            if profile_resp.status_code == 200:
                profile = profile_resp.json()
                return_data["description"] = profile.get("description") or None
                if profile.get("created"):
                    return_data["joined"] = profile["created"][:10]
                return_data["is_banned"] = profile.get("isBanned", False)

            # fetch live avatar headshot
            try:
                av_head = requests.get(
                    f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false",
                    headers=headers,
                    impersonate="chrome120",
                    timeout=8,
                )
                if av_head.status_code == 200:
                    av_data = av_head.json().get("data", [])
                    if av_data and av_data[0].get("imageUrl"):
                        return_data["avatar_url"] = av_data[0]["imageUrl"]
                        return_data["avatar_headshot"] = av_data[0]["imageUrl"]
            except Exception:
                pass

            # fetch live 3D avatar body render
            try:
                av_body = requests.get(
                    f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png&isCircular=false",
                    headers=headers,
                    impersonate="chrome120",
                    timeout=8,
                )
                if av_body.status_code == 200:
                    body_data = av_body.json().get("data", [])
                    if body_data and body_data[0].get("imageUrl"):
                        return_data["avatar_render"] = body_data[0]["imageUrl"]
                        if "avatar_url" not in return_data:
                            return_data["avatar_url"] = body_data[0]["imageUrl"]
            except Exception:
                pass

            # get friends/follower counts
            counts_resp = requests.get(
                f"https://friends.roblox.com/v1/users/{user_id}/followers/count",
                headers=headers,
                impersonate="chrome120",
                timeout=10,
            )
            if counts_resp.status_code == 200:
                return_data["followers"] = counts_resp.json().get("count", 0)

            friends_resp = requests.get(
                f"https://friends.roblox.com/v1/users/{user_id}/friends/count",
                headers=headers,
                impersonate="chrome120",
                timeout=10,
            )
            if friends_resp.status_code == 200:
                return_data["friends"] = friends_resp.json().get("count", 0)

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
    _res = roblox_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
