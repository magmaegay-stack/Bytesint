import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def osintphone_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "osintphone",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    phone_digits = clean.lstrip("+")

    return_data = {"phone": clean}
    found_something = False

    # 1. Try 800notes.com (US numbers)
    try:
        resp = requests.get(
            f"https://800notes.com/Phone.aspx/{clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # extract summary
            summary = soup.find("div", {"id": "sai_sum"}) or soup.find("div", class_=re.compile(r"summary|result"))
            if summary:
                text = summary.get_text(separator=" ", strip=True)[:300]
                if text and len(text) > 10:
                    return_data["notes_summary"] = text
                    found_something = True

            # check spam reports
            spam_m = re.search(r'(\d+)\s+(?:report|comment)', resp.text, re.IGNORECASE)
            if spam_m:
                return_data["reports_count"] = int(spam_m.group(1))
                found_something = True

            # tags
            tag_section = soup.find("div", class_=re.compile(r"tag|category"))
            if tag_section:
                tags = [t.get_text(strip=True) for t in tag_section.find_all(["span", "a"]) if t.get_text(strip=True)]
                if tags:
                    return_data["tags"] = tags[:5]
                    found_something = True
    except Exception:
        pass

    # 2. Try shouldianswer.net (redirects to chistachiamando.it for IT numbers)
    try:
        resp2 = requests.get(
            f"https://www.shouldianswer.net/phone-number/{phone_digits}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )
        if resp2.status_code == 200:
            html2 = resp2.text
            rating_m = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html2)
            if rating_m:
                return_data["safety_rating"] = float(rating_m.group(1))
                found_something = True

            count_m = re.search(r'"ratingCount"\s*:\s*"?(\d+)"?', html2)
            if count_m:
                return_data["rating_count"] = int(count_m.group(1))
    except Exception:
        pass

    if found_something:
        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v is not None}
    else:
        result["result"] = "not_found"
        result["return"] = {"status": "no_data_found"}

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = osintphone_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
