import sys
import json
import re
import io
import os
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def tumblr_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@").lower()

    result = {
        "target": clean,
        "service": "tumblr",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    url = f"https://www.tumblr.com/{clean}"

    try:
        resp = requests.get(
            url,
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        final_url = resp.url
        if "tumblr.com/login" in final_url or "tumblr.com/register" in final_url:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code == 301 or resp.status_code == 302:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        text = resp.text

        if "There's nothing here." in text or "this tumblr doesn't exist" in text.lower():
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        soup = BeautifulSoup(text, "html.parser")

        return_data = {
            "username": clean,
            "profile_url": url,
            "status": "verified_active",
        }

        # Titolo blog dall'OG tag
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
            name = re.sub(r"\s*[\|–\-]\s*Tumblr.*$", "", title, flags=re.IGNORECASE).strip()
            if name and name.lower() not in ("tumblr", ""):
                return_data["blog_title"] = name

        # Descrizione
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"].strip()
            if desc:
                return_data["description"] = desc[:300]

        # Avatar
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            img = og_img["content"].strip()
            if img:
                return_data["avatar_url"] = img

        # Conta i post visibili
        posts = soup.find_all("article")
        if posts:
            return_data["visible_posts"] = len(posts)

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = tumblr_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
