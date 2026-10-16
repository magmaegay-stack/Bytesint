import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def letterboxd_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "letterboxd",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        resp = requests.get(
            f"https://letterboxd.com/{clean}/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome124",
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

            if "page not found" in html.lower() or "sorry, we can't find that page" in html.lower():
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            return_data = {
                "username": clean,
                "profile_url": f"https://letterboxd.com/{clean}/",
                "status": "verified_active",
            }

            # display name
            name_el = soup.find("h1", class_=re.compile(r"person|title|name"))
            if not name_el:
                name_el = soup.find(["h1", "h2"], class_=re.compile(r"profile"))
            if name_el:
                return_data["display_name"] = name_el.get_text(strip=True)

            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content") and not return_data.get("display_name"):
                title = og_title["content"].replace("• Letterboxd", "").strip()
                if title:
                    return_data["display_name"] = title

            # bio
            bio_el = soup.find("div", class_=re.compile(r"bio|about"))
            if bio_el:
                return_data["bio"] = bio_el.get_text(strip=True)[:200]

            # avatar
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                return_data["avatar_url"] = og_img["content"]

            # films count
            films_m = re.search(r'([\d,]+)\s+Films', html, re.IGNORECASE)
            if films_m:
                return_data["films_watched"] = films_m.group(1).replace(",", "")

            # followers
            stats = soup.find("section", class_=re.compile(r"profile-stats|stats"))
            if stats:
                for a in stats.find_all("a"):
                    href = a.get("href", "")
                    val = a.get_text(strip=True)
                    if "followers" in href:
                        return_data["followers"] = val
                    elif "following" in href:
                        return_data["following"] = val

            # location
            location_el = soup.find(class_=re.compile(r"location"))
            if location_el:
                return_data["location"] = location_el.get_text(strip=True)

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
    _res = letterboxd_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
