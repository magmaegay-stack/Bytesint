import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def lastfm_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "lastfm",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        resp = requests.get(
            f"https://www.last.fm/user/{clean}",
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

            if "this user does not exist" in html.lower() or "page not found" in html.lower():
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            return_data = {
                "username": clean,
                "profile_url": f"https://www.last.fm/user/{clean}",
                "status": "verified_active",
            }

            # real name
            name_el = soup.find("span", class_=re.compile(r"header-title|user-title|profile-name"))
            if name_el:
                return_data["display_name"] = name_el.get_text(strip=True)

            # og tags fallback
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content") and not return_data.get("display_name"):
                title = og_title["content"].replace("| Last.fm", "").replace("Last.fm User", "").strip()
                if title:
                    return_data["display_name"] = title

            # avatar
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                return_data["avatar_url"] = og_img["content"]

            # scrobbles count
            scrobbles_m = re.search(r'([\d,]+)\s+Scrobbles', html, re.IGNORECASE)
            if scrobbles_m:
                return_data["scrobbles"] = scrobbles_m.group(1).replace(",", "")

            # country
            country_el = soup.find("dd", class_=re.compile(r"country"))
            if not country_el:
                country_m = re.search(r'"location"\s*:\s*"([^"]+)"', html)
                if country_m:
                    return_data["location"] = country_m.group(1)

            # member since
            joined_m = re.search(r'(?:Joined|Member since)[:\s]+([A-Za-z]+ \d{4}|\d{1,2} [A-Za-z]+ \d{4})', html, re.IGNORECASE)
            if joined_m:
                return_data["joined"] = joined_m.group(1)

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
    _res = lastfm_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
