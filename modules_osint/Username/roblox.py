import json
import os
import sys
from datetime import datetime, timezone

def http_get(url: str, headers: dict = None, timeout: int = 10):
    hdr = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    if headers:
        hdr.update(headers)

    # 1. curl_cffi
    try:
        from curl_cffi import requests as cffi_req
        r = cffi_req.get(url, headers=hdr, impersonate="chrome120", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # 2. requests
    try:
        import requests
        r = requests.get(url, headers=hdr, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # 3. urllib
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass

    return None

def http_post(url: str, json_data: dict, headers: dict = None, timeout: int = 12):
    hdr = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers:
        hdr.update(headers)

    # 1. curl_cffi
    try:
        from curl_cffi import requests as cffi_req
        r = cffi_req.post(url, headers=hdr, json=json_data, impersonate="chrome120", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # 2. requests
    try:
        import requests
        r = requests.post(url, headers=hdr, json=json_data, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # 3. urllib
    try:
        import urllib.request
        data_bytes = json.dumps(json_data).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=hdr, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass

    return None

def roblox_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "roblox",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        user_id = None
        user_name = clean
        display_name = None

        # Check if target is a numeric Roblox User ID
        if clean.isdigit():
            user_id = int(clean)
            p_data = http_get(f"https://users.roblox.com/v1/users/{user_id}")
            if p_data and isinstance(p_data, dict) and p_data.get("id"):
                user_name = p_data.get("name", clean)
                display_name = p_data.get("displayName")
            else:
                user_id = None

        if not user_id:
            # Search by username via users API
            search_data = http_post(
                "https://users.roblox.com/v1/usernames/users",
                json_data={"usernames": [clean], "excludeBannedUsers": False},
            )
            users = search_data.get("data", []) if search_data and isinstance(search_data, dict) else []

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
            profile = http_get(f"https://users.roblox.com/v1/users/{user_id}")
            if profile and isinstance(profile, dict):
                return_data["description"] = profile.get("description") or None
                if profile.get("created"):
                    return_data["joined"] = profile["created"][:10]
                return_data["is_banned"] = profile.get("isBanned", False)

            # fetch live avatar headshot
            av_head = http_get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false")
            if av_head and isinstance(av_head, dict):
                av_data = av_head.get("data", [])
                if av_data and av_data[0].get("imageUrl"):
                    return_data["avatar_url"] = av_data[0]["imageUrl"]
                    return_data["avatar_headshot"] = av_data[0]["imageUrl"]

            # fetch live 3D avatar body render
            av_body = http_get(f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png&isCircular=false")
            if av_body and isinstance(av_body, dict):
                body_data = av_body.get("data", [])
                if body_data and body_data[0].get("imageUrl"):
                    return_data["avatar_render"] = body_data[0]["imageUrl"]
                    if "avatar_url" not in return_data:
                        return_data["avatar_url"] = body_data[0]["imageUrl"]

            # get friends/follower counts
            followers_data = http_get(f"https://friends.roblox.com/v1/users/{user_id}/followers/count")
            if followers_data and isinstance(followers_data, dict):
                return_data["followers"] = followers_data.get("count", 0)

            friends_data = http_get(f"https://friends.roblox.com/v1/users/{user_id}/friends/count")
            if friends_data and isinstance(friends_data, dict):
                return_data["friends"] = friends_data.get("count", 0)

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v is not None and v != ""}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('{"error": "missing argument"}')
        sys.exit(1)
    res = roblox_lookup(sys.argv[1].strip())
    print(json.dumps(res, indent=4, ensure_ascii=False))
