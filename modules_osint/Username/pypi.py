import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def pypi_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@").lower()

    result = {
        "target": clean,
        "service": "pypi",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        # PyPI user profile page
        resp = requests.get(
            f"https://pypi.org/user/{clean}/",
            headers={**headers, "Accept": "text/html"},
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        html = resp.text

        if "We could not find" in html or "does not exist" in html.lower():
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "username": clean,
            "profile_url": f"https://pypi.org/user/{clean}/",
            "status": "verified_active",
        }

        # extract packages from the profile
        packages = re.findall(r'href="/project/([^/]+)/"', html)
        if packages:
            return_data["packages"] = list(dict.fromkeys(packages))[:20]  # unique, max 20
            return_data["packages_count"] = len(return_data["packages"])

        # display name
        name_m = re.search(r'<h1[^>]*class="[^"]*username[^"]*"[^>]*>([^<]+)<', html)
        if not name_m:
            name_m = re.search(r'<span[^>]*class="[^"]*username[^"]*"[^>]*>([^<]+)<', html)
        if name_m:
            return_data["display_name"] = name_m.group(1).strip()

        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if og_title:
            return_data["display_name"] = og_title.group(1).replace("PyPI", "").strip("– ").strip()

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
    _res = pypi_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
