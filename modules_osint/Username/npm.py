import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def npm_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@").lower()

    result = {
        "target": clean,
        "service": "npm",
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
            f"https://registry.npmjs.org/-/v1/search?text=maintainer:{clean}&size=1",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
        )

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        data = resp.json()
        total = data.get("total", 0)

        return_data = {
            "username": clean,
            "profile_url": f"https://www.npmjs.com/~{clean}",
            "status": "verified_active",
            "packages_count": total,
        }

        if data.get("objects"):
            pkg = data["objects"][0].get("package", {})
            if pkg.get("author", {}).get("name"):
                return_data["display_name"] = pkg["author"]["name"]
            elif pkg.get("publisher", {}).get("username"):
                return_data["display_name"] = pkg["publisher"]["username"]

        # also check profile page directly
        profile_resp = requests.get(
            f"https://www.npmjs.com/~{clean}",
            headers={**headers, "Accept": "text/html"},
            impersonate="chrome120",
            timeout=10,
        )

        if profile_resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if profile_resp.status_code == 200:
            import re
            html = profile_resp.text
            if "Not Found" in html or "404" in html[:200]:
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if og_title:
                return_data["display_name"] = og_title.group(1).replace("| npm", "").strip()

            # count packages from profile
            pkgs_m = re.search(r'(\d+)\s+[Pp]ackage', html)
            if pkgs_m:
                return_data["packages_count"] = int(pkgs_m.group(1))

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
    _res = npm_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
