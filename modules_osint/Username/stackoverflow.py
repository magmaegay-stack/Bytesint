import json
import os
import re
import gzip
import urllib.request
import urllib.parse
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")


def stackoverflow_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "stackoverflow",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        # StackExchange public API — no key needed, 300 req/day unauthenticated
        params = urllib.parse.urlencode({
            "inname": clean, "site": "stackoverflow",
            "order": "desc", "sort": "reputation",
            "filter": "default", "pagesize": 10,
        })
        req = urllib.request.Request(
            f"https://api.stackexchange.com/2.3/users?{params}",
            headers={"Accept-Encoding": "gzip", "User-Agent": "python-urllib/3.11"},
        )
        with urllib.request.urlopen(req, timeout=15) as _r:
            raw = _r.read()
            if _r.info().get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
        data = json.loads(raw)
        items = data.get("items", [])

        if not items:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        # Find exact match by display_name or account name
        best = None
        for user in items:
            name = user.get("display_name", "")
            if name.lower() == clean.lower():
                best = user
                break
        if not best:
            best = items[0]

        return_data = {
            "username": clean,
            "display_name": best.get("display_name"),
            "profile_url": best.get("link"),
            "user_id": str(best.get("user_id", "")),
            "reputation": best.get("reputation"),
            "badge_bronze": best.get("badge_counts", {}).get("bronze"),
            "badge_silver": best.get("badge_counts", {}).get("silver"),
            "badge_gold": best.get("badge_counts", {}).get("gold"),
            "location": best.get("location"),
            "website": best.get("website_url"),
            "avatar_url": best.get("profile_image"),
            "account_type": best.get("account_type"),
            "status": "verified_active",
        }

        if best.get("creation_date"):
            from datetime import datetime as _dt
            return_data["joined"] = _dt.fromtimestamp(best["creation_date"]).strftime("%Y-%m-%d")

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v is not None and v != "" and v != 0}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = stackoverflow_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
