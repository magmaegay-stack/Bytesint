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

def fiton_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    url = f"https://fitonapp.com/user/{clean_target}"
    
    result = {
        "target": clean_target,
        "service": "fiton",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code != 200 or "404" in response.url:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        result["result"] = "found"
        result["return"] = {"username": clean_target, "profile_url": url, "status": "verified_active"}
    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = fiton_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
