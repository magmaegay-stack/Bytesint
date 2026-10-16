import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def netflix_lookup(email: str) -> dict:
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

            try:
                page.goto("https://www.netflix.com/LoginHelp", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # Accetta cookie consent
                try:
                    page.click("button:has-text('Accept')", timeout=3000)
                    page.wait_for_timeout(800)
                except Exception:
                    pass

                # Seleziona radio "Email" se presente
                try:
                    radios = page.locator("input[name=forgotPasswordChoice]").all()
                    for r in radios:
                        val = r.get_attribute("value") or ""
                        if "email" in val.lower():
                            r.click()
                            break
                except Exception:
                    pass

                page.wait_for_timeout(300)

                # Riempi email
                page.fill("input[name=email]", email.strip())
                page.wait_for_timeout(500)

                # Clicca "Email Me"
                try:
                    page.click("button:has-text('Email Me')", timeout=5000)
                except Exception:
                    page.keyboard.press("Enter")

                page.wait_for_timeout(5000)
                content = page.content().lower()
                url = page.url
                result["raw"] = {"url": url}

                # Email trovata → pagina di conferma invio email (frasi uniche alla pagina successo)
                found_phrases = [
                    "email sent",        # H1 titolo pagina successo
                    "has been sent to",  # "has been sent to xx@..." solo in conferma
                    "check your spam",   # solo in conferma invio
                ]
                # Email non trovata → errore generico o rimane sul form
                not_found_phrases = [
                    "sorry, something went wrong",
                    "we couldn't find",
                    "can't find an account",
                    "no account found",
                ]

                for phrase in found_phrases:
                    if phrase in content:
                        result["accountExists"] = True
                        result["raw"]["reason"] = f"phrase: '{phrase}'"
                        break

                if result["accountExists"] is None:
                    for phrase in not_found_phrases:
                        if phrase in content:
                            result["accountExists"] = False
                            result["raw"]["reason"] = f"phrase: '{phrase}'"
                            break

                if "browse" in url:
                    result["accountExists"] = True
                    result["raw"]["reason"] = "redirected to browse"

            except PWTimeout:
                result["rate_limited"] = True
                result["raw"] = {"error": "timeout"}
            finally:
                browser.close()

    except Exception as e:
        result["raw"] = {"error": str(e)}

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = netflix_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
