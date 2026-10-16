import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def line_lookup(phone: str) -> dict:
    """Check LINE messenger registration via phone number."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "line",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    phone_digits = clean.lstrip("+")

    try:
        # LINE invite link — works for users who have a phone-based account
        resp = requests.get(
            f"https://line.me/R/ti/p/~{phone_digits}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # LINE shows a profile page if user is found
            if "line://ti/p/" in html or "addFriend" in html or "add-friend" in html.lower():
                return_data["registered"] = True
                return_data["add_friend_url"] = f"https://line.me/R/ti/p/~{phone_digits}"

                og_title = soup.find("meta", property="og:title")
                if og_title and og_title.get("content"):
                    name = og_title["content"].strip()
                    if name and "line" not in name.lower():
                        return_data["display_name"] = name

                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"):
                    return_data["avatar_url"] = og_img["content"]

                result["result"] = "found"
                result["return"] = {k: v for k, v in return_data.items() if v}
            else:
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}
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
    _res = line_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
