import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def keybase_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@").lower()

    result = {
        "target": clean,
        "service": "keybase",
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
            f"https://keybase.io/_/api/1.0/user/lookup.json?username={clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
        )

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        data = resp.json()

        if data.get("status", {}).get("code") != 0 or not data.get("them"):
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        them = data["them"]
        basics = them.get("basics", {})
        profile = them.get("profile", {})
        proofs = them.get("proofs_summary", {}).get("all", [])

        return_data = {
            "username": basics.get("username", clean),
            "profile_url": f"https://keybase.io/{clean}",
            "status": "verified_active",
            "uid": them.get("id"),
            "full_name": profile.get("full_name") or None,
            "location": profile.get("location") or None,
            "bio": profile.get("bio") or None,
            "followers": them.get("tracking_stats", {}).get("followers", 0),
            "following": them.get("tracking_stats", {}).get("followees", 0),
        }

        # proof links
        proof_data = {}
        for proof in proofs:
            service = proof.get("proof_type", "")
            phandle = proof.get("nametag") or proof.get("display_markup") or ""
            if service and phandle:
                proof_data[service] = phandle
        if proof_data:
            return_data["proofs"] = proof_data

        # key fingerprint
        key = them.get("public_keys", {}).get("primary", {})
        if key.get("key_fingerprint"):
            return_data["pgp_fingerprint"] = key["key_fingerprint"]

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
    _res = keybase_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
