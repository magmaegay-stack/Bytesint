import sys
import json
import io
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == 'nt':
    os.system('chcp 65001 >nul')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def twitter_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@').lower()
    url = f"https://api.fxtwitter.com/{clean_target}"
    
    result = {
        "target": clean_target,
        "service": "twitter",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OSINT-Suite/1.0",
        "Accept": "application/json"
    }

    try:
        resp = requests.get(
            url,
            headers=headers,
            impersonate="chrome120",
            timeout=10,
            allow_redirects=True
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists", "http_status": 404}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"Errore HTTP: {resp.status_code}"
            return result

        data = resp.json()
        
        if "user" in data:
            user_info = data["user"]
            
            # Recuperiamo i contatori gestendo entrambe le possibili chiavi dell'API
            followers = user_info.get("followers") or user_info.get("followers_count", 0)
            following = user_info.get("following") or user_info.get("following_count", 0)
            
            result["result"] = "found"
            result["return"] = {
                "identifier": user_info.get("screen_name", clean_target),
                "profile_name": user_info.get("name", "N/D"),
                "bio": user_info.get("description", "N/D"),
                "followers_count": followers,
                "following_count": following,
                "profile_image": user_info.get("avatar_url", "N/D"),
                "profile_url": f"https://x.com/{clean_target}",
                "status": "verified_active" if user_info.get("verified") else "active",
                "http_status": resp.status_code
            }
        else:
            result["result"] = "not_found"
            result["return"] = {
                "identifier": clean_target,
                "status": "not_exists",
                "http_status": resp.status_code
            }

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
