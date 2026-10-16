import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def amazon_lookup(email: str) -> dict:
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
                page.goto(
                    "https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0"
                    "&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F"
                    "&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select"
                    "&openid.assoc_handle=usflex"
                    "&openid.mode=checkid_setup"
                    "&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select"
                    "&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0",
                    timeout=30000,
                    wait_until="domcontentloaded",
                )
                page.wait_for_timeout(1500)

                # Riempi email
                page.fill("input[name=email], input[type=email]", email.strip())
                page.wait_for_timeout(400)

                # Clicca Continue
                try:
                    page.click("input[id='continue']", timeout=3000)
                except Exception:
                    try:
                        page.click("input[type=submit]", timeout=3000)
                    except Exception:
                        page.keyboard.press("Enter")

                page.wait_for_timeout(4000)
                content = page.content()
                url = page.url
                content_lower = content.lower()
                result["raw"] = {"url": url}

                if "api/fwcim" in url or "validateCaptcha" in url or "captcha" in url.lower():
                    result["rate_limited"] = True
                    result["raw"]["reason"] = "captcha_page"
                    browser.close()
                    return result

                # Amazon /ax/claim o /claim/intent → email non registrata, offre di creare account
                if "/ax/claim" in url or "/claim/intent" in url:
                    result["accountExists"] = False
                    result["raw"]["reason"] = "redirected_to_claim_new_account"
                    browser.close()
                    return result

                # Amazon mostra campo password se email esiste
                found_phrases = [
                    'name="password"',
                    "enter your password",
                    "forgot your password",
                    "to better protect your account",
                ]
                not_found_phrases = [
                    "we cannot find an account",
                    "we can't find an account",
                    "no account found",
                    "create a new amazon account",
                    "create account",
                    "there is no account",
                    "sign up",
                ]

                # Controlla se c'è il campo password nella pagina
                if 'name="password"' in content and "create account" not in content_lower[:3000]:
                    result["accountExists"] = True
                    result["raw"]["reason"] = "password_field_found"
                    browser.close()
                    return result

                for phrase in found_phrases:
                    if phrase.lower() in content_lower:
                        result["accountExists"] = True
                        result["raw"]["reason"] = f"phrase: '{phrase}'"
                        browser.close()
                        return result

                for phrase in not_found_phrases:
                    if phrase.lower() in content_lower:
                        result["accountExists"] = False
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
    _res = amazon_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
