import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def viber_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "viber",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    phone_digits = clean.lstrip("+")

    try:
        resp = requests.get(
            f"https://invite.viber.com/?g2=AAAAAA&number=%2B{phone_digits}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            html = resp.text

            if "viber://" in html.lower() or "open viber" in html.lower():
                return_data["registered"] = True
                return_data["invite_url"] = f"viber://add?number=%2B{phone_digits}"
                return_data["web_invite_url"] = f"https://invite.viber.com/?g2=AAAAAA&number=%2B{phone_digits}"

                name_m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
                if name_m:
                    name = name_m.group(1).strip()
                    if name and "viber" not in name.lower():
                        return_data["display_name"] = name

                result["result"] = "found"
                result["return"] = {k: v for k, v in return_data.items() if v is not None}
            elif "invalid" in html.lower() or "not found" in html.lower():
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
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
    _res = viber_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
