import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def whatsapp_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "whatsapp",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        # WhatsApp click-to-chat link — if the number is registered the page loads properly
        phone_clean = clean.lstrip("+")
        resp = requests.get(
            f"https://wa.me/{phone_clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            html = resp.text

            # WhatsApp returns a page with the number if it exists
            if "Click to Chat" in html or "click to chat" in html.lower() or "wa.me" in html:
                # Check if WhatsApp says the number isn't registered
                if "this phone number is not on WhatsApp" in html.lower():
                    result["result"] = "not_found"
                    result["return"] = {"status": "not_registered"}
                    return result

                return_data["registered"] = True
                return_data["status"] = "registered_on_whatsapp"
                return_data["click_to_chat_url"] = f"https://wa.me/{phone_clean}"

                # extract name/business from og tags
                og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                if og_title:
                    name = og_title.group(1).replace("WhatsApp", "").strip().strip("-").strip()
                    if name:
                        return_data["display_name"] = name

                result["result"] = "found"
                result["return"] = return_data
            else:
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
        else:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = whatsapp_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
