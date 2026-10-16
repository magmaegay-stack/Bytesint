# language: Python 3.10+, file: paypal.py
import sys
import json
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
COOKIES_JSON = HERE / ".paypal_cookies.json"

def search_paypal(target: str):
    if not COOKIES_JSON.exists():
        print(json.dumps({"error": "File .paypal_cookies.json non trovato"}, indent=2))
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
            "domain": c.get("domain", ".paypal.com"),
            "path": c.get("path", "/")
        }
        if c.get("expirationDate"):
            cookie["expires"] = c.get("expirationDate")
        playwright_cookies.append(cookie)

    with sync_playwright() as p:
        # headless=True: gira invisibile in background senza aprire finestre (perfetto per migliaia di ricerche)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        context.add_cookies(playwright_cookies)
        page = context.new_page()

        try:
            page.goto("https://www.paypal.com/myaccount/transfer/homepage", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            if "signin" in page.url.lower() or "login" in page.url.lower():
                print(json.dumps({"error": "I cookie sono scaduti o non validi. Riesporta i cookie freschi."}, indent=2))
                browser.close()
                return

            search_input = page.locator("input[placeholder*='Nome'], input[placeholder*='name'], input[placeholder*='email'], input[placeholder*='cellulare'], input[type='text']").first
            search_input.wait_for(timeout=20000)
            
            search_input.click()
            page.wait_for_timeout(500)
            search_input.fill(target)
            
            page.wait_for_timeout(3500)

            results = []
            items = page.locator("li[role='menuitem'], [role='option']").all()
            
            for item in items:
                try:
                    target_el = item.locator("[fullname], [networkid], [networkkiddisplayname]").first
                    if target_el.count() == 0:
                        target_el = item

                    fullname = target_el.get_attribute("fullname") or item.get_attribute("fullname")
                    net_disp = target_el.get_attribute("networkkiddisplayname") or item.get_attribute("networkkiddisplayname")
                    net_id = target_el.get_attribute("networkid") or item.get_attribute("networkid")
                    payer_id = target_el.get_attribute("payerid") or item.get_attribute("payerid")
                    
                    if not fullname:
                        text = item.inner_text()
                        if text:
                            lines = [l.strip() for l in text.split("\n") if l.strip()]
                            if lines:
                                fullname = lines[0]
                                for l in lines:
                                    if "@" in l:
                                        net_disp = l
                                        break

                    username = net_disp
                    if not username and net_id:
                        username = f"@{net_id}"
                    if username and not str(username).startswith("@"):
                        username = f"@{username}"

                    img = item.locator("img").first
                    avatar_url = img.get_attribute("src") if img.count() > 0 else None
                    if not avatar_url:
                        avatar_url = target_el.get_attribute("thumbnailurl") or item.get_attribute("thumbnailurl")

                    if fullname and fullname.lower() not in ["paypal", "invia", ""]:
                        if not any(r["display_name"] == fullname and r["username"] == username for r in results):
                            results.append({
                                "display_name": fullname,
                                "username": username,
                                "avatar_url": avatar_url,
                                "profile_id": payer_id
                            })
                except Exception:
                    continue

            output = {
                "exists": len(results) > 0,
                "target": target,
                "results": results
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
    search_paypal(_sys.argv[1].strip())
