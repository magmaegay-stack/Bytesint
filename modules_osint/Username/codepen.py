import json
import os
import sys
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup


def lookup(target):
    clean = target.strip().lstrip("@")
    result = {
        "target": clean,
        "service": "codepen",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }
    try:
        resp = cffi_requests.get(
            f"https://codepen.io/{clean}",
            impersonate="chrome124",
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        soup = BeautifulSoup(resp.text, "html.parser")
        return_data = {
            "username": clean,
            "profile_url": f"https://codepen.io/{clean}",
        }

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            name = og_title["content"].replace("on CodePen", "").strip()
            if name:
                return_data["display_name"] = name

        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return_data["bio"] = og_desc["content"][:300]

        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            img = og_img["content"]
            if "default" not in img:
                return_data["avatar_url"] = img

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v}
    except Exception as e:
        result["result"] = "error"
        result["return"] = {"error": str(e)}
    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    print(json.dumps(lookup(_sys.argv[1].strip()), indent=4, ensure_ascii=False))
