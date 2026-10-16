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

def plex_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    url = f"https://app.plex.tv/desktop#!/users/{clean_target}"
    
    result = {
        "target": clean_target,
        "service": "plex",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "X-Plex-Client-Identifier": "osint-toolkit"
    }

    try:
        # Endpoint pubblico di ricerca account Plex
        api_url = f"https://plex.tv/api/v2/users/search?query={clean_target}"
        response = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                result["result"] = "found"
                result["return"] = {
                    "username": clean_target,
                    "status": "verified_active",
                    "details": data
                }
                return result

        result["result"] = "not_found"
        result["return"] = {"status": "not_exists"}
    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = plex_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
