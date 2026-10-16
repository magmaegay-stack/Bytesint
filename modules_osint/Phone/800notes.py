import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def notes800_lookup(phone: str) -> dict:
    """800notes.com — user-reported spam/scam phone number database."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "800notes",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    # 800notes is US/Canada only — format: 1-NXX-NXX-XXXX (no +)
    try:
        import phonenumbers
        pn = phonenumbers.parse(clean, None)
        cc = pn.country_code
        if cc not in (1,):  # only NANP countries
            result["result"] = "not_found"
            result["return"] = {"status": "not_us_number", "note": "800notes covers US/Canada only"}
            return result
        national = str(pn.national_number)
        # format as 1-NXX-NXX-XXXX
        url_phone = f"1-{national[:3]}-{national[3:6]}-{national[6:]}"
    except Exception:
        # fallback: strip + and try
        digits = clean.lstrip("+")
        if not digits.startswith("1") or len(digits) < 10:
            result["result"] = "not_found"
            result["return"] = {"status": "not_us_number"}
            return result
        d = digits[1:]
        url_phone = f"1-{d[:3]}-{d[3:6]}-{d[6:]}"

    try:
        resp = requests.get(
            f"https://800notes.com/Phone.aspx/{url_phone}",
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

            # summary section
            summary = (soup.find("div", {"id": "sai_sum"})
                       or soup.find("div", class_=re.compile(r"summary|result")))
            if summary:
                text = summary.get_text(separator=" ", strip=True)[:400]
                if text and len(text) > 10:
                    return_data["summary"] = text

            # spam reports count
            spam_m = re.search(r'(\d+)\s+(?:report|comment|note)', html, re.IGNORECASE)
            if spam_m:
                return_data["reports_count"] = int(spam_m.group(1))

            # tags/categories
            tag_section = soup.find("div", class_=re.compile(r"tag|category|label"))
            if tag_section:
                tags = [t.get_text(strip=True) for t in tag_section.find_all(["span", "a"])
                        if t.get_text(strip=True) and len(t.get_text(strip=True)) < 30]
                if tags:
                    return_data["tags"] = list(dict.fromkeys(tags))[:8]

            # recent comments
            comments = []
            for comment_div in soup.find_all("div", class_=re.compile(r"comment|note|post"))[:5]:
                text = comment_div.get_text(separator=" ", strip=True)
                if text and len(text) > 10:
                    comments.append(text[:200])
            if comments:
                return_data["recent_reports"] = comments

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
    _res = notes800_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
