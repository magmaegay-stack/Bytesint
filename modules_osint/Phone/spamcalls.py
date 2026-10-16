import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def spamcalls_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "spamcalls",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    phone_digits = clean.lstrip("+")

    try:
        resp = requests.get(
            f"https://spamcalls.net/en/search/{phone_digits}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            count_m = re.search(r'(\d+)\s+(?:report|comment|call)', html, re.IGNORECASE)
            if count_m:
                return_data["reports_count"] = int(count_m.group(1))

            rating_m = re.search(r'"ratingValue"\s*[=:]\s*"?([\d.]+)"?', html)
            if rating_m:
                return_data["rating"] = float(rating_m.group(1))

            # spam risk level (from <h3 class="typ"><span>Spam-Risk</span><strong>Low/High</strong>)
            risk_m = re.search(r'Spam-Risk[^<]{0,30}<strong>([^<]{2,30})</strong>', html, re.IGNORECASE)
            if not risk_m:
                # fallback: h3 class=typ contains "Spam-RiskLow" concatenated
                for tag in soup.find_all("h3", class_="typ"):
                    text = tag.get_text(strip=True)
                    m2 = re.search(r'Spam-Risk\s*(.+)', text, re.IGNORECASE)
                    if m2:
                        return_data["spam_risk"] = m2.group(1).strip()
                        break
            else:
                return_data["spam_risk"] = risk_m.group(1).strip()

            # card-title headings contain "local_phone+39" (carrier code) and "publicItaly" (country)
            for tag in soup.find_all("h3", class_="card-title"):
                text = tag.get_text(strip=True)
                # "publicItaly" → country
                m3 = re.search(r'^public([A-Z][a-z][a-zA-Z ]+)$', text)
                if m3 and not return_data.get("country"):
                    return_data["country"] = m3.group(1).strip()

            # location from sentence "is coming from Italy"
            loc_m = re.search(r'is coming from\s*([A-Za-z ,]+?)[\.\(]', html, re.IGNORECASE)
            if loc_m and not return_data.get("country"):
                return_data["country"] = loc_m.group(1).strip()

            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v is not None}
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
    _res = spamcalls_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
