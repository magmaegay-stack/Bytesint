import sys
import json
import io
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == 'nt':
    os.system('chcp 65001 >nul')

def snapchat_lookup(target: str) -> dict:
    clean = target.strip().lstrip('@')

    result = {
        "target": clean,
        "service": "snapchat",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    url = f"https://www.snapchat.com/add/{clean}"

    try:
        resp = requests.get(
            url, headers=headers, impersonate="chrome120",
            timeout=15, allow_redirects=True
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        text = resp.text

        # Snapchat restituisce una pagina generica se l'utente non esiste
        not_found_phrases = [
            "Sorry, we couldn't find",
            "couldn't find this profile",
            "page doesn't exist",
            "Sorry, we can",
        ]
        for phrase in not_found_phrases:
            if phrase.lower() in text.lower():
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

        soup = BeautifulSoup(text, "html.parser")

        return_data = {
            "username": clean,
            "profile_url": url,
            "status": "verified_active",
        }

        # Display name dall'OG title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
            if title and title.lower() not in ("snapchat", ""):
                # Rimuove "Snapchat" dal titolo se presente
                name = re.sub(r'\s+(on Snapchat|[\|–\-]\s*Snapchat.*)$', '', title, flags=re.IGNORECASE).strip()
                if name:
                    return_data["display_name"] = name

        # Descrizione
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"].strip()
            if desc and "snapchat" not in desc.lower():
                return_data["bio"] = desc

        # Avatar
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            img_url = og_img["content"].strip()
            if img_url and "snapchat" not in img_url.lower():
                return_data["avatar_url"] = img_url

        # Snapcode (immagine QR specifica di Snapchat)
        snapcode_match = re.search(r'(https://app\.snapchat\.com/web/deeplink/snapcode[^\s"\']+)', text)
        if snapcode_match:
            return_data["snapcode_url"] = snapcode_match.group(1)

        # Subscribers dalla pagina (se esposta nel JSON-LD o nel testo)
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld and json_ld.string:
            try:
                ld = json.loads(json_ld.string)
                if isinstance(ld, list):
                    ld = ld[0]
                if ld.get("name"):
                    return_data["display_name"] = ld["name"]
                if ld.get("description"):
                    return_data["bio"] = ld["description"]
                if ld.get("image"):
                    return_data["avatar_url"] = ld["image"] if isinstance(ld["image"], str) else ld["image"].get("url", "")
                subs = ld.get("interactionStatistic")
                if isinstance(subs, list):
                    for stat in subs:
                        if stat.get("interactionType", "").endswith("FollowAction"):
                            return_data["subscribers"] = stat.get("userInteractionCount")
                elif isinstance(subs, dict) and subs.get("interactionType", "").endswith("FollowAction"):
                    return_data["subscribers"] = subs.get("userInteractionCount")
            except Exception:
                pass

        if not return_data.get("display_name") and not og_title:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        result["result"] = "found"
        result["return"] = return_data

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = snapchat_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
