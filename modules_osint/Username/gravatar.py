import json
import os
import hashlib
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def gravatar_lookup(target: str) -> dict:
    """Look up Gravatar by username (probes common email providers)."""
    clean = target.strip().lstrip("@").lower()

    result = {
        "target": clean,
        "service": "gravatar",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    # probe multiple common email formats
    email_guesses = [
        f"{clean}@gmail.com",
        f"{clean}@yahoo.com",
        f"{clean}@hotmail.com",
        f"{clean}@outlook.com",
        f"{clean}@protonmail.com",
    ]

    try:
        s = requests.Session(impersonate="chrome120")

        for email in email_guesses:
            md5 = hashlib.md5(email.encode("utf-8")).hexdigest()
            resp = s.get(
                f"https://www.gravatar.com/{md5}.json",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122",
                },
                timeout=10,
            )

            if resp.status_code == 200:
                d = resp.json()
                entry = d.get("entry", [{}])[0]
                if entry.get("id"):
                    return_data = {
                        "username": entry.get("preferredUsername", clean),
                        "display_name": entry.get("displayName"),
                        "profile_url": entry.get("profileUrl"),
                        "avatar_url": entry.get("thumbnailUrl"),
                        "status": "verified_active",
                        "matched_email_hash": md5,
                        "matched_email_provider": email.split("@")[1],
                    }

                    if entry.get("aboutMe"):
                        return_data["bio"] = entry["aboutMe"][:200]
                    if entry.get("currentLocation"):
                        return_data["location"] = entry["currentLocation"]
                    if entry.get("name"):
                        n = entry["name"]
                        if n.get("formatted"):
                            return_data["full_name"] = n["formatted"]
                    if entry.get("emails"):
                        return_data["emails"] = [e.get("value") for e in entry["emails"] if e.get("value")]
                    if entry.get("urls"):
                        return_data["urls"] = [u.get("value") for u in entry["urls"][:5] if u.get("value")]
                    if entry.get("accounts"):
                        return_data["linked_accounts"] = [
                            {"service": a.get("shortname"), "url": a.get("url")}
                            for a in entry["accounts"][:10] if a.get("shortname")
                        ]

                    result["result"] = "found"
                    result["return"] = {k: v for k, v in return_data.items() if v}
                    return result

        result["result"] = "not_found"
        result["return"] = {"status": "not_found_on_common_providers"}

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
