import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def shouldianswer_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "shouldianswer",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    # Use digits only without leading +
    phone_digits = clean.lstrip("+")

    try:
        resp = requests.get(
            f"https://www.shouldianswer.net/phone-number/{phone_digits}",
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
            from bs4 import BeautifulSoup
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            body_text = soup.get_text(separator="\n", strip=True)

            # JSON-LD rating
            rating_m = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html)
            if rating_m:
                return_data["safety_rating"] = float(rating_m.group(1))

            count_m = re.search(r'"ratingCount"\s*:\s*"?(\d+)"?', html)
            if count_m:
                return_data["rating_count"] = int(count_m.group(1))

            # Line type from page text (e.g. "line cellulare" or "line fissa")
            lt_m = re.search(r'line\s+(cellulare|fissa|mobile|landline|voip)', body_text, re.IGNORECASE)
            if lt_m:
                raw = lt_m.group(1).lower()
                return_data["line_type"] = "mobile" if raw in ("cellulare", "mobile") else raw

            # Country
            country_m = re.search(r'\b(Italy|France|Germany|Spain|UK|United Kingdom|USA|United States)\b', body_text, re.IGNORECASE)
            if country_m:
                return_data["country"] = country_m.group(1)

            # Reports/comments count
            comments_m = re.search(r'(\d+)\s+(?:comment|report|review|valutazion)', body_text, re.IGNORECASE)
            if comments_m:
                return_data["reports"] = int(comments_m.group(1))

            # Category (telemarketing, scam, etc.)
            cat_m = re.search(r'"category"\s*:\s*"([^"]+)"', html)
            if cat_m:
                return_data["category"] = cat_m.group(1)

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
    _res = shouldianswer_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
