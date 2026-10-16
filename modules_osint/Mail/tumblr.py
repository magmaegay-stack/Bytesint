import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def tumblr_lookup(email: str) -> dict:
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
                page.goto("https://www.tumblr.com/forgot_password", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # Accetta cookie se presente
                for btn in ["Accept all", "Accept", "OK"]:
                    try:
                        page.click(f"button:has-text('{btn}')", timeout=2000)
                        page.wait_for_timeout(500)
                        break
                    except Exception:
                        pass

                # Riempi email — Tumblr usa input[name=email] con type=text
                try:
                    page.fill("input[name=email]", email.strip())
                except Exception:
                    try:
                        page.fill("input[type=email]", email.strip())
                    except Exception:
                        page.locator("input[placeholder*='mail' i]").first.fill(email.strip())

                page.wait_for_timeout(500)

                # Submit
                try:
                    page.click("button[type=submit]", timeout=5000)
                except Exception:
                    page.keyboard.press("Enter")

                page.wait_for_timeout(5000)
                content = page.content().lower()
                url = page.url
                result["raw"] = {"url": url}

                not_found_phrases = [
                    "we couldn't find",
                    "no account found",
                    "that email isn't associated",
                    "doesn't exist",
                    "can't find an account",
                    "we don't have an account",
                ]
                found_phrases = [
                    "check your email",
                    "we sent",
                    "email has been sent",
                    "reset link sent",
                    "we've sent",
                    "sent an email",
                    "email was sent",
                ]

                for phrase in not_found_phrases:
                    if phrase in content:
                        result["accountExists"] = False
                        result["raw"]["reason"] = f"phrase: '{phrase}'"
                        break

                if result["accountExists"] is None:
                    for phrase in found_phrases:
                        if phrase in content:
                            result["accountExists"] = True
                            result["raw"]["reason"] = f"phrase: '{phrase}'"
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
    _res = tumblr_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
