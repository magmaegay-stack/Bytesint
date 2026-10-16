import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def threads_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "threads",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        resp = requests.get(
            f"https://www.threads.net/@{clean}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            if "sorry, this page isn't available" in html.lower() or "page not found" in html.lower():
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            return_data = {
                "username": clean,
                "profile_url": f"https://www.threads.net/@{clean}",
                "status": "verified_active",
            }

            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].replace("| Threads", "").strip()
                if title and "threads" not in title.lower():
                    return_data["display_name"] = title

            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = og_desc["content"].strip()
                if desc and "threads" not in desc.lower():
                    return_data["bio"] = desc[:200]

            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                return_data["avatar_url"] = og_img["content"]

            # Try extracting from __bbox JSON
            bbox_m = re.search(r'__bbox\s*=\s*(\{.+?\});</script>', html, re.DOTALL)
            if bbox_m:
                try:
                    bbox = json.loads(bbox_m.group(1))
                    user_data = (bbox.get("require", [[]])[0][3][0]
                                     .get("__bbox", {})
                                     .get("result", {})
                                     .get("data", {})
                                     .get("data", {})
                                     .get("user") or {})
                    if user_data.get("full_name"):
                        return_data["display_name"] = user_data["full_name"]
                    if user_data.get("biography"):
                        return_data["bio"] = user_data["biography"][:200]
                    if user_data.get("follower_count"):
                        return_data["followers"] = user_data["follower_count"]
                    if user_data.get("profile_pic_url"):
                        return_data["avatar_url"] = user_data["profile_pic_url"]
                    if user_data.get("is_verified"):
                        return_data["is_verified"] = user_data["is_verified"]
                except Exception:
                    pass

            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v}
        else:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = threads_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
