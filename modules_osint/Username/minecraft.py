import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def minecraft_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "minecraft",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        # Mojang API: get UUID by username
        resp = requests.get(
            f"https://api.mojang.com/users/profiles/minecraft/{clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
        )

        if resp.status_code == 404 or resp.status_code == 204:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        data = resp.json()
        uuid = data.get("id", "")
        name = data.get("name", clean)

        return_data = {
            "username": name,
            "uuid": uuid,
            "profile_url": f"https://namemc.com/profile/{clean}",
            "status": "verified_active",
            "is_demo": data.get("demo", False),
            "is_legacy": data.get("legacy", False),
        }

        # format UUID with dashes
        if len(uuid) == 32:
            return_data["uuid_formatted"] = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"

        # skin/head image
        return_data["skin_url"] = f"https://crafatar.com/renders/head/{uuid}?overlay"
        return_data["avatar_url"] = f"https://crafatar.com/avatars/{uuid}?overlay"

        # get profile including name history (via session server)
        profile_resp = requests.get(
            f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}",
            headers=headers,
            impersonate="chrome120",
            timeout=10,
        )
        if profile_resp.status_code == 200:
            profile = profile_resp.json()
            props = profile.get("properties", [])
            for prop in props:
                if prop.get("name") == "textures":
                    import base64
                    try:
                        tex_data = json.loads(base64.b64decode(prop["value"]).decode())
                        skin = tex_data.get("textures", {}).get("SKIN", {})
                        if skin.get("url"):
                            return_data["skin_texture_url"] = skin["url"]
                        cape = tex_data.get("textures", {}).get("CAPE", {})
                        if cape.get("url"):
                            return_data["cape_url"] = cape["url"]
                    except Exception:
                        pass

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v is not None and v is not False and v != ""}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = minecraft_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
