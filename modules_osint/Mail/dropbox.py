import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup


def dropbox_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                viewport={"width": 1366, "height": 768},
            )
            page = ctx.new_page()

            # Cattura risposte dell'API interna di Dropbox
            api_responses = []

            def on_response(resp):
                url = resp.url
                if "dropbox.com" in url and resp.status not in (204,):
                    if any(x in url for x in ["/forgot", "/account", "/users", "reset", "password"]):
                        try:
                            body = resp.text()
                            api_responses.append({"url": url, "status": resp.status, "body": body[:500]})
                        except Exception:
                            pass

            page.on("response", on_response)

            try:
                page.goto("https://www.dropbox.com/forgot", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # Riempi email
                page.fill("input[type=email]", email.strip())
                page.wait_for_timeout(400)

                # Submit e cattura il cambio DOM
                page.click("button[type=submit]", timeout=5000)
                page.wait_for_timeout(6000)

                url = page.url
                result["raw"] = {"url": url, "api": api_responses}

                # Controlla il testo della pagina per messaggi di successo/errore
                content = page.content().lower()

                # Dropbox mostra "If there's a Dropbox account associated..."
                # sia per email trovate che non trovate (enumeration protection)
                generic_sent = [
                    "if there's a dropbox account",
                    "if an account exists",
                    "we'll send you an email",
                    "check your spam folder",
                    "email was sent",
                    "we sent an email",
                ]
                not_found = [
                    "can't find your account",
                    "no account found",
                    "we couldn't find",
                ]

                for phrase in not_found:
                    if phrase in content:
                        result["accountExists"] = False
                        result["raw"]["reason"] = f"phrase: '{phrase}'"
                        break

                if result["accountExists"] is None:
                    for phrase in generic_sent:
                        if phrase in content:
                            # Dropbox ha enumeration protection - dice sempre "se esiste ti mandiamo email"
                            result["accountExists"] = None
                            result["raw"]["reason"] = "enumeration_protected"
                            break

                # Controlla le risposte API per distinguere
                for api_r in api_responses:
                    body_lower = api_r.get("body", "").lower()
                    if "not_found" in body_lower or '"status": 404' in body_lower:
                        result["accountExists"] = False
                        result["raw"]["reason"] = "api_not_found"
                        break
                    if api_r.get("status") == 200 and "reset" in api_r.get("url", ""):
                        result["accountExists"] = True
                        result["raw"]["reason"] = "api_reset_200"
                        break

            except PWTimeout:
                result["rate_limited"] = True
                result["raw"] = {"error": "timeout"}
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

    except Exception as e:
        result["raw"] = {"error": str(e)}

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = dropbox_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
