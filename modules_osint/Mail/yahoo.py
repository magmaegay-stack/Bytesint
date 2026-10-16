import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def yahoo_lookup(email: str) -> dict:
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
                page.goto("https://login.yahoo.com/", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)

                # Riempi username/email
                try:
                    page.fill("input[name=username]", email.strip())
                except Exception:
                    page.locator("input").first.fill(email.strip())

                page.wait_for_timeout(400)

                # Clicca Next
                try:
                    page.click("input[name=signin], button[name=signin], #login-signin, button[type=submit]", timeout=5000)
                except Exception:
                    page.keyboard.press("Enter")

                page.wait_for_timeout(4000)
                url = page.url
                result["raw"] = {"url": url}

                # Yahoo con Gmail → redirect a Google OAuth = account esiste
                if "accounts.google.com" in url:
                    result["accountExists"] = True
                    result["raw"]["reason"] = "redirected_to_google_oauth"
                    browser.close()
                    return result

                # Yahoo con Microsoft → redirect a Microsoft OAuth = account esiste
                if "login.microsoftonline.com" in url or "live.com" in url:
                    result["accountExists"] = True
                    result["raw"]["reason"] = "redirected_to_microsoft_oauth"
                    browser.close()
                    return result

                # Pagina sfida Yahoo (password) → account trovato
                if "challenge" in url and "yahoo.com" in url:
                    result["accountExists"] = True
                    result["raw"]["reason"] = "challenge_page_found"
                    browser.close()
                    return result

                content = page.content().lower()

                # Controlla se è sulla pagina di inserimento password
                if 'name="passwd"' in content or 'name="password"' in content:
                    result["accountExists"] = True
                    result["raw"]["reason"] = "password_field_found"
                    browser.close()
                    return result

                # Messaggi di errore Yahoo
                not_found_phrases = [
                    "that yahoo id does not exist",
                    "doesn't match a yahoo account",
                    "no account found",
                    "we couldn't find",
                    "yahoo id doesn't exist",
                    "account not found",
                ]
                for phrase in not_found_phrases:
                    if phrase in content:
                        result["accountExists"] = False
                        result["raw"]["reason"] = f"phrase: '{phrase}'"
                        browser.close()
                        return result

                # Se reindirizzato al login Yahoo con challenge → account esiste
                found_phrases = [
                    "enter your password",
                    "two-step verification",
                    "sign in smarter",
                ]
                for phrase in found_phrases:
                    if phrase in content:
                        result["accountExists"] = True
                        result["raw"]["reason"] = f"phrase: '{phrase}'"
                        browser.close()
                        return result

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
    _res = yahoo_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
