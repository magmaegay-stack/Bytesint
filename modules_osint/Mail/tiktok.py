import sys
import json
import io
import os
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == 'nt':
    os.system('chcp 65001 >nul')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# INCOLLA QUI I COOKIE PRESI DALL'F12 (STORAGE)
# ==========================================
MANUAL_COOKIES = {
    "sessionid": "9438a146ab7e1b4aebfb25e72af1c6e8",      # Incolla qui il valore completo di sessionid[cite: 3]
    "msToken": "XsB7oixyLkC3lvHzSq4i5K5kWUY6Gy6UbRV2YuCwwkyF6_ecXG0g-mswDIKrDNjF3ES6kYZ8pjtyhApesTzFpds8MFZe6_M2HYUAGW7YG_C4GDpQNdNKyKxZuzpEAc4CxbcE7ayrVz1-JSgwYdc77Dh_brhw-urJ",        # Incolla qui il valore completo di msToken[cite: 3]
    "odin_tt": "97bc34b5c18b3872e8e936d8449fd7a7ac3662d90f20c9715dad81a6a961944a2556d7d88a6d2adddcb9462dd2f6fb78a8a7c95e49bf71316c3a702205e9abea843f137678732aa6aaaa43c17e3b4f69",        # Incolla qui il valore completo di odin_tt[cite: 3]
    "sid_tt": "9438a146ab7e1b4aebfb25e72af1c6e8"          # Incolla qui il valore completo di sid_tt[cite: 3]
}

def tiktok_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    url = f"https://www.tiktok.com/@{clean_target}"
    
    result = {
        "target": clean_target,
        "service": "tiktok",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        # Filtriamo eventuali cookie lasciati vuoti per pulizia
        active_cookies = {k: v for k, v in MANUAL_COOKIES.items() if v.strip()}

        response = requests.get(
            url, 
            headers=headers, 
            cookies=active_cookies if active_cookies else None,
            impersonate="chrome120", 
            timeout=15, 
            allow_redirects=True
        )
        
        if response.status_code != 200 or "login" in response.url.lower():
            result["result"] = "not_found"
            result["return"] = {
                "identifier": clean_target,
                "status": "not_exists_or_login_required",
                "http_status": response.status_code
            }
            return result

        soup = BeautifulSoup(response.text, 'html.parser')
        
        profile_name = "N/D"
        profile_image = "N/D"
        bio = "N/D"
        is_found = False

        # Estrazione dal blocco JSON di idratazione interna di TikTok
        hydration_script = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
        if hydration_script and hydration_script.string:
            try:
                data = json.loads(hydration_script.string)
                default_scope = data.get("__DEFAULT_SCOPE__", {})
                user_detail = default_scope.get("webapp.user-detail", {})
                user_info = user_detail.get("userInfo", {}).get("user", {})
                
                if user_info:
                    profile_name = user_info.get("nickname", clean_target)
                    profile_image = user_info.get("avatarLarger") or user_info.get("avatarMedium") or "N/D"
                    bio = user_info.get("signature", "N/D")
                    is_found = True
            except Exception:
                pass

        # Fallback sui meta tag OpenGraph se il blocco JSON non basta
        if not is_found:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                profile_name = og_title.get("content").strip()

            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                profile_image = og_img.get("content").strip()

            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                bio = og_desc.get("content").strip()

            if profile_name != "N/D" and profile_name.lower() != "tiktok":
                is_found = True

        page_text = soup.get_text().lower()
        if "account not found" in page_text or "couldn't find this account" in page_text:
            result["result"] = "not_found"
            result["return"] = {
                "identifier": clean_target,
                "status": "not_exists",
                "http_status": response.status_code
            }
            return result

        if not is_found and profile_name == "N/D":
            result["result"] = "not_found"
            result["return"] = {
                "identifier": clean_target,
                "status": "not_exists",
                "http_status": response.status_code
            }
            return result

        result["result"] = "found"
        result["return"] = {
            "identifier": clean_target,
            "profile_name": profile_name,
            "bio": bio,
            "profile_image": profile_image,
            "profile_url": response.url,
            "status": "verified_active",
            "http_status": response.status_code
        }

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = tiktok_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
