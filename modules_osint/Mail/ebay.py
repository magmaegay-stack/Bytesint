import sys
import json
import re
from curl_cffi import requests


def ebay_lookup(email: str) -> dict:
    result = {
        "accountExists": None,
        "rate_limited": False,
        "raw": None,
    }

    session = requests.Session(impersonate="chrome120")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.ebay.com",
    }

    try:
        # Visita la pagina forgot password di eBay
        page = session.get(
            "https://signin.ebay.com/ws/eBayISAPI.dll?ForgotPassword",
            headers=headers,
            timeout=15,
            allow_redirects=True,
        )

        # Estrai token _gh
        gh_token = re.search(r'name="_gh"\s+value="([^"]+)"', page.text)
        srt = re.search(r'name="srt"\s+value="([^"]+)"', page.text)
        pid = re.search(r'name="pid"\s+value="([^"]+)"', page.text)

        form_data = {
            "_gh": gh_token.group(1) if gh_token else "",
            "srt": srt.group(1) if srt else "",
            "pid": pid.group(1) if pid else "",
            "userid": email.strip(),
            "MfcISAPICommand": "ForgotPassword",
            "siteid": "0",
            "co_partnerId": "0",
            "UsingSSL": "1",
            "ru": "",
            "pp": "",
            "rq": "",
            "pa1": "",
            "pa2": "",
            "pa3": "",
            "i1": "-1",
            "pageType": "-1",
            "Submit": "Continue",
        }

        resp = session.post(
            "https://signin.ebay.com/ws/eBayISAPI.dll?ForgotPassword",
            headers={
                **headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://signin.ebay.com/ws/eBayISAPI.dll?ForgotPassword",
            },
            data=form_data,
            timeout=15,
            allow_redirects=True,
        )

        status = resp.status_code
        text = resp.text
        url = resp.url
        result["raw"] = {"status_code": status, "url": url}

        if status == 429:
            result["rate_limited"] = True
            return result

        text_lower = text.lower()

        not_found_phrases = [
            "no account found",
            "we couldn't find",
            "not found",
            "doesn't match",
            "no member",
            "invalid user id or email address",
            "we didn't find",
            "can't find",
        ]
        found_phrases = [
            "we've sent",
            "email has been sent",
            "check your email",
            "sent to your email",
            "reset password email",
            "an email was sent",
        ]

        for phrase in not_found_phrases:
            if phrase in text_lower:
                result["accountExists"] = False
                result["raw"]["reason"] = f"phrase: '{phrase}'"
                return result

        for phrase in found_phrases:
            if phrase in text_lower:
                result["accountExists"] = True
                result["raw"]["reason"] = f"phrase: '{phrase}'"
                return result

        return result

    except Exception as e:
        result["raw"] = {"error": str(e)}
        return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = ebay_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
