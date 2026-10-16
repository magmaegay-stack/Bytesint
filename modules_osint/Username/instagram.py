# language: Python 3.10+, file: instagram.py
import sys
import json
import re
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
COOKIES_JSON = HERE / ".instagram_cookie.json"

def search_instagram(username: str):
    clean_username = username.lstrip("@").strip()
    
    if not COOKIES_JSON.exists():
        print(json.dumps({"error": "File .instagram_cookie.json non trovato"}, indent=2))
        return

    try:
        cookies_raw = json.loads(COOKIES_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"error": f"Errore lettura cookie: {e}"}, indent=2))
        return

    playwright_cookies = []
    for c in cookies_raw:
        cookie = {
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/")
        }
        if c.get("expirationDate"):
            cookie["expires"] = c.get("expirationDate")
        playwright_cookies.append(cookie)

    with sync_playwright() as p:
        # Gira invisibile in background (headless=True) per evitare crash con volumi alti
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        context.add_cookies(playwright_cookies)
        page = context.new_page()

        try:
            url = f"https://www.instagram.com/{clean_username}/"
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)

            # Verifica se Instagram richiede il login (cookie scaduti)
            if "accounts/login" in page.url.lower():
                print(json.dumps({"error": "I cookie di Instagram sono scaduti o non validi (richiesto login)."}, indent=2))
                browser.close()
                return

            # Estrazione sicura tramite i tag Meta OpenGraph (estremamente stabili)
            title_el = page.locator("meta[property='og:title']").first
            image_el = page.locator("meta[property='og:image']").first
            desc_el = page.locator("meta[property='og:description']").first

            og_title = title_el.get_attribute("content") if title_el.count() > 0 else ""
            avatar_url = image_el.get_attribute("content") if image_el.count() > 0 else None
            og_desc = desc_el.get_attribute("content") if desc_el.count() > 0 else ""

            display_name = clean_username
            if og_title:
                parts = og_title.split("(@")
                if len(parts) > 0:
                    display_name = parts[0].strip()

            followers = None
            following = None
            posts = None

            if og_desc:
                # Estrae metriche da stringhe tipo "1.2M Followers, 300 Following, 45 Posts..."
                match_followers = re.search(r'([\d\.,]+[KM]?) Followers', og_desc, re.IGNORECASE)
                match_following = re.search(r'([\d\.,]+[KM]?) Following', og_desc, re.IGNORECASE)
                match_posts = re.search(r'([\d\.,]+[KM]?) Posts', og_desc, re.IGNORECASE)

                if match_followers:
                    followers = match_followers.group(1)
                if match_following:
                    following = match_following.group(1)
                if match_posts:
                    posts = match_posts.group(1)

            output = {
                "exists": True,
                "username": clean_username,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "followers": followers,
                "following": following,
                "posts": posts,
                "bio_description": og_desc
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))

        except Exception as e:
            print(json.dumps({"error": str(e)}, indent=2))
        finally:
            browser.close()

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = search_instagram(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
