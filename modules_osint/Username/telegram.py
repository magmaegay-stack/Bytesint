import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def telegram_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "telegram",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        resp = requests.get(
            f"https://t.me/{clean}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome120",
            timeout=12,
            allow_redirects=True,
        )

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Generic template for non-existent usernames
            not_found_phrases = [
                "if you have telegram, you can contact",
                "channel doesn't seem to exist",
                "bot doesn't seem to exist",
                "user doesn't seem to exist",
                "sorry, but you can't",
            ]
            if any(p in html.lower() for p in not_found_phrases):
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            # Real profiles have a non-empty tgme_page_title
            title_el = soup.find("div", class_="tgme_page_title")
            if not title_el or not title_el.get_text(strip=True):
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            return_data = {
                "username": clean,
                "profile_url": f"https://t.me/{clean}",
                "status": "verified_active",
                "display_name": title_el.get_text(strip=True),
            }

            # description
            desc_el = soup.find("div", class_="tgme_page_description")
            if desc_el:
                return_data["description"] = desc_el.get_text(strip=True)[:300]

            # subscriber/member count
            extra_el = soup.find("div", class_="tgme_page_extra")
            if extra_el:
                count_m = re.search(
                    r'([\d\s,]+)\s*(subscriber|member|follower)',
                    extra_el.get_text(), re.IGNORECASE
                )
                if count_m:
                    return_data["subscribers"] = count_m.group(1).strip().replace(" ", "")

            # avatar
            img_el = soup.find("img", class_="tgme_page_photo_image")
            if img_el and img_el.get("src"):
                return_data["avatar_url"] = img_el["src"]

            # account type detection
            if "tgme_page_action_button" in html:
                if "Join" in html:
                    return_data["account_type"] = "channel_or_group"
                elif "Send Message" in html:
                    return_data["account_type"] = "user_or_bot"

            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v}

        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = telegram_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
