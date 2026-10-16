import json
import os
import re
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
        "service": "substack",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }
    try:
        resp = cffi_requests.get(
            f"https://substack.com/@{clean}",
            impersonate="chrome124",
            timeout=15,
            allow_redirects=True,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.text.strip() if title_tag else ""

        # Not-found page: 'Search "username" on Substack'
        if "search" in title.lower() and clean.lower() in title.lower():
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "username": clean,
            "profile_url": f"https://substack.com/@{clean}",
        }

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            display = og_title["content"].replace("| Substack", "").strip()
            if display and "substack" not in display.lower():
                return_data["display_name"] = display

        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return_data["bio"] = og_desc["content"][:300]

        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            return_data["avatar_url"] = og_img["content"]

        subs_m = re.search(r"([\d,]+)\s+subscriber", resp.text, re.IGNORECASE)
        if subs_m:
            return_data["subscribers"] = subs_m.group(1).replace(",", "")

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
