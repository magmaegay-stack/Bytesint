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

def gitlab_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    # GitLab utilizza un endpoint di ricerca utenti basato su query string
    url = f"https://gitlab.com/api/v4/users?username={clean_target}"
    
    result = {
        "target": clean_target,
        "service": "gitlab",
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

        users = response.json()
        if not users or not isinstance(users, list) or len(users) == 0:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        # Prendiamo il primo utente corrispondente alla ricerca esatta dello username
        user_data = None
        for u in users:
            if u.get("username", "").lower() == clean_target.lower():
                user_data = u
                break
        
        if not user_data:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "user_id": user_data.get("id"),
            "username": user_data.get("username"),
            "profile_url": user_data.get("web_url"),
            "status": "verified_active"
        }

        if user_data.get("name"):
            return_data["profile_name"] = user_data.get("name")
        
        if user_data.get("state"):
            return_data["account_state"] = user_data.get("state")

        if user_data.get("avatar_url"):
            return_data["avatar_url"] = user_data.get("avatar_url")

        # Campi aggiuntivi opzionali (se configurati pubblicamente dall'utente)
        if user_data.get("bio"):
            return_data["bio"] = user_data.get("bio")

        if user_data.get("location"):
            return_data["location"] = user_data.get("location")

        if user_data.get("website_url"):
            return_data["website"] = user_data.get("website_url")

        if user_data.get("public_email"):
            return_data["email"] = user_data.get("public_email")

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
    _res = gitlab_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
