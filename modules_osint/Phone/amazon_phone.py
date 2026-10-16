import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")

# Country code → Amazon domain mapping
_AMAZON_DOMAIN = {
    "IT": "amazon.it", "DE": "amazon.de", "FR": "amazon.fr",
    "ES": "amazon.es", "GB": "amazon.co.uk", "JP": "amazon.co.jp",
    "IN": "amazon.in", "CA": "amazon.ca", "AU": "amazon.com.au",
    "BR": "amazon.com.br", "MX": "amazon.com.mx", "NL": "amazon.nl",
    "SE": "amazon.se", "PL": "amazon.pl", "TR": "amazon.com.tr",
    "AE": "amazon.ae", "SA": "amazon.sa", "SG": "amazon.sg",
}


def _get_region(phone_clean: str) -> str:
    try:
        import phonenumbers
        pn = phonenumbers.parse("+" + phone_clean, None)
        return phonenumbers.region_code_for_number(pn) or "US"
    except Exception:
        return "US"


def amazon_phone_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "amazon_phone",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        phone_clean = clean.lstrip("+")
        region = _get_region(phone_clean)
        domain = _AMAZON_DOMAIN.get(region, "amazon.com")
        base_url = f"https://www.{domain}"

        # Amazon assoc_handle by region
        assoc_map = {
            "IT": "itflex", "DE": "deflex", "FR": "frflex",
            "ES": "esflex", "GB": "gbflex", "JP": "jpflex",
            "IN": "inflex", "CA": "caflex", "AU": "auflex",
            "BR": "brflex", "MX": "mxflex", "NL": "nlflex",
        }
        assoc = assoc_map.get(region, "usflex")

        s = requests.Session()
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        from urllib.parse import urlencode, quote
        oidc_params = urlencode({
            "openid.pape.max_auth_age": "0",
            "openid.return_to": f"{base_url}/",
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.assoc_handle": assoc,
            "openid.mode": "checkid_setup",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.ns": "http://specs.openid.net/auth/2.0",
        })

        # Step 1: GET forgot password page with openid params (required for form to load)
        r0 = s.get(
            f"{base_url}/ap/forgotpassword?{oidc_params}",
            headers={
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=20,
            verify=False,
            allow_redirects=True,
        )

        if r0.status_code != 200:
            # Try amazon.com as fallback
            base_url = "https://www.amazon.com"
            oidc_params_us = urlencode({
                "openid.pape.max_auth_age": "0",
                "openid.return_to": f"{base_url}/",
                "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
                "openid.assoc_handle": "usflex",
                "openid.mode": "checkid_setup",
                "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
                "openid.ns": "http://specs.openid.net/auth/2.0",
            })
            r0 = s.get(
                f"{base_url}/ap/forgotpassword?{oidc_params_us}",
                headers={"User-Agent": ua, "Accept": "text/html,application/xhtml+xml"},
                timeout=20,
                verify=False,
                allow_redirects=True,
            )

        soup0 = BeautifulSoup(r0.text, "html.parser")

        # Extract form action and ALL hidden inputs
        form = soup0.find("form", id=re.compile(r"forgot|auth", re.IGNORECASE)) or soup0.find("form")
        form_action = f"{base_url}/ap/forgotpassword"
        post_data = {}

        if form:
            action = form.get("action", "")
            if action:
                form_action = action if action.startswith("http") else base_url + action
            for inp in form.find_all("input", {"type": ["hidden", "submit"]}):
                name = inp.get("name", "")
                val = inp.get("value", "")
                if name:
                    post_data[name] = val

        # Set the phone/email field
        email_field = "email"
        for inp in soup0.find_all("input"):
            inp_name = inp.get("name", "").lower()
            if "email" in inp_name or "phone" in inp_name or "username" in inp_name:
                email_field = inp.get("name", "email")
                break
        post_data[email_field] = clean

        # Step 2: POST the form
        resp = s.post(
            form_action,
            headers={
                "User-Agent": ua,
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": base_url,
                "Referer": f"{base_url}/ap/forgotpassword",
            },
            data=post_data,
            timeout=20,
            verify=False,
            allow_redirects=True,
        )

        html = resp.text
        return_data = {"phone": clean}
        html_lower = html.lower()

        found_phrases = [
            "we've sent a one-time password",
            "we sent a one-time",
            "enter the otp",
            "verify your identity",
            "confirm your identity",
            "code has been sent",
            "ein einmalpasswort",
            "abbiamo inviato",
            "codice di verifica",
            "un codice",
        ]
        not_found_phrases = [
            "cannot find an account",
            "we cannot find an account",
            "no account found",
            "didn't find",
            "non troviamo",
            "kein konto",
            "aucun compte",
        ]

        if any(p in html_lower for p in found_phrases):
            return_data["registered"] = True
            return_data["status"] = "account_found_otp_sent"
            mask_m = re.search(r'[a-zA-Z*]+@[a-zA-Z*]+\.[a-z]{2,}', html)
            if mask_m:
                return_data["masked_email"] = mask_m.group(0)
            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v}

        elif any(p in html_lower for p in not_found_phrases):
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}

        elif "captcha" in html_lower or "puzzle" in html_lower:
            result["result"] = "error"
            result["msg"] = "captcha_required"

        else:
            snippet = html[:500].replace("\n", " ").strip()
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code} — unknown_response"

    except Exception as e:
        msg = str(e)
        if "Resolving timed out" in msg or "SSL" in msg or "ssl" in msg.lower():
            result["result"] = "error"
            result["msg"] = "service_unreachable_network_block"
        else:
            result["result"] = "error"
            result["msg"] = msg

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = amazon_phone_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
