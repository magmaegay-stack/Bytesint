import json
import os
from datetime import datetime, timezone
import urllib.request
import urllib.error

if os.name == "nt":
    os.system("chcp 65001 >nul")


def dockerhub_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@").lower()

    result = {
        "target": clean,
        "service": "dockerhub",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    def _api_get(url):
        req = urllib.request.Request(url, headers={
            "User-Agent": "docker/24.0.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())

    try:
        try:
            status, data = _api_get(f"https://hub.docker.com/v2/users/{clean}/")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result
            result["result"] = "error"
            result["msg"] = f"HTTP {e.code}"
            return result

        return_data = {
            "username": data.get("username", clean),
            "profile_url": f"https://hub.docker.com/u/{clean}",
            "status": "verified_active",
            "full_name": data.get("full_name") or None,
            "company": data.get("company") or None,
            "location": data.get("location") or None,
            "bio": data.get("bio") or None,
            "website": data.get("profile_url") or None,
            "gravatar_url": data.get("gravatar_url") or None,
        }

        if data.get("date_joined"):
            return_data["joined"] = data["date_joined"][:10]

        try:
            _, repos_data = _api_get(f"https://hub.docker.com/v2/repositories/{clean}/?page_size=1")
            return_data["public_repos"] = repos_data.get("count", 0)
        except Exception:
            pass

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
    _res = dockerhub_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
