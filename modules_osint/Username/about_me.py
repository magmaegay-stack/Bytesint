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
        "service": "about_me",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }
    try:
        resp = cffi_requests.get(
            f"https://about.me/{clean}",
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
            "profile_url": f"https://about.me/{clean}",
        }

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            name = og_title["content"].replace("on about.me", "").strip()
            if name:
                return_data["display_name"] = name

        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"]
            if "about.me" not in desc.lower():
                return_data["bio"] = desc[:300]

        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            return_data["avatar_url"] = og_img["content"]

        # Look for website/social links in the page
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            return_data["canonical_url"] = canonical["href"]

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
