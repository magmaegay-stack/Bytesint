import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def whocalld_lookup(phone: str) -> dict:
    """whocalld.com — reverse phone lookup with spam reports."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "whocalld",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    phone_digits = clean.lstrip("+")

    try:
        resp = requests.get(
            f"https://whocalld.com/+{phone_digits}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
            verify=False,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # extract all meaningful text lines
            body_text = soup.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]

            # line type + carrier from sentence: "This seems to be a mobile phone. The carrier for this number is Vodafone."
            type_m = re.search(
                r'This\s+(?:seems\s+to\s+be|is)\s+(?:a\s+)?(\w[\w ]*?)\s+phone',
                html, re.IGNORECASE
            )
            if type_m:
                return_data["line_type"] = type_m.group(1).strip().lower()

            carrier_m = re.search(
                r'The\s+carrier[^.]*?\s+is\s+([A-Za-z][^\s.][^.\n<]{0,40})\.',
                html, re.IGNORECASE
            )
            if carrier_m:
                return_data["carrier"] = carrier_m.group(1).strip()

            # country — first short word that looks like a country name after phone number heading
            for line in lines:
                if (len(line) > 2 and len(line) < 40
                        and line not in ("Whocalld",)
                        and not any(c.isdigit() for c in line)
                        and line.istitle()):
                    # potential country
                    return_data["location"] = line
                    break

            # spam/safety rating
            rating_m = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html)
            if rating_m:
                return_data["safety_rating"] = float(rating_m.group(1))

            # reports count
            count_m = re.search(r'(\d+)\s+(?:report|search|complaint)', html, re.IGNORECASE)
            if count_m:
                return_data["reports"] = int(count_m.group(1))

            # caller name (if named entry)
            name_m = re.search(r'(?:Name|Caller)[:\s]+([A-Z][a-zA-Z ]{3,40})', html)
            if name_m:
                return_data["caller_name"] = name_m.group(1).strip()

            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v is not None}
        elif resp.status_code == 404:
            result["result"] = "not_found"
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
    _res = whocalld_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
