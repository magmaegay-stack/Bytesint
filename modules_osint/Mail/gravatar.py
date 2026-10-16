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

def gravatar_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@').lower()
    url = f"https://en.gravatar.com/{clean_target}.json"
    
    result = {
        "target": clean_target,
        "service": "gravatar",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            url, 
            headers=headers, 
            impersonate="chrome120", 
            timeout=15
        )
        
        if response.status_code != 200:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        data = response.json()
        entries = data.get("entry", [])
        
        if not entries or not isinstance(entries, list) or len(entries) == 0:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        user_data = entries[0]

        return_data = {
            "profile_url": user_data.get("profileUrl"),
            "hash": user_data.get("hash"),
            "status": "verified_active"
        }

        if user_data.get("displayName"):
            return_data["display_name"] = user_data.get("displayName")
            
        if user_data.get("aboutMe"):
            return_data["bio"] = user_data.get("aboutMe")
            
        if user_data.get("currentLocation"):
            return_data["location"] = user_data.get("currentLocation")
            
        if user_data.get("thumbnailUrl"):
            return_data["avatar_url"] = user_data.get("thumbnailUrl")

        # Estrazione di account e siti web verificati collegati a Gravatar
        accounts = user_data.get("accounts", [])
        if accounts:
            connected_accounts = []
            for acc in accounts:
                connected_accounts.append({
                    "service": acc.get("shortname"),
                    "name": acc.get("name"),
                    "url": acc.get("url")
                })
            return_data["connected_accounts"] = connected_accounts

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
    _res = gravatar_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
