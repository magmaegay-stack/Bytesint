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

def keybase_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    url = f"https://keybase.io/_/api/1.0/user/lookup.json?usernames={clean_target}"
    
    result = {
        "target": clean_target,
        "service": "keybase",
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
        them = data.get("them")
        
        if not them or len(them) == 0 or them[0] is None:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        user_data = them[0]
        profile = user_data.get("profile", {})

        return_data = {
            "profile_url": f"https://keybase.io/{clean_target}",
            "status": "verified_active"
        }

        if profile.get("full_name"):
            return_data["full_name"] = profile.get("full_name")
        
        if profile.get("bio"):
            return_data["bio"] = profile.get("bio")

        if profile.get("location"):
            return_data["location"] = profile.get("location")

        # Estrazione delle prove sociali collegate (altri account associati)
        proofs_summary = user_data.get("proofs_summary", {})
        all_proofs = proofs_summary.get("all", [])
        if all_proofs:
            connected_accounts = []
            for proof in all_proofs:
                connected_accounts.append({
                    "type": proof.get("proof_type"),
                    "name": proof.get("nametag"),
                    "url": proof.get("service_url")
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
    _res = keybase_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
