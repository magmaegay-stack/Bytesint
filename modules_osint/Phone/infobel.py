import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def infobel_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "infobel",
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
        phone_clean = clean.lstrip("+")
        resp = requests.get(
            f"https://www.infobel.com/en/world/phone/{phone_clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=20,
            allow_redirects=True,
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_found"}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        return_data = {"phone": clean}

        # extract name if listed
        name_tag = soup.find("h1", class_=re.compile(r"name|title|result"))
        if name_tag:
            return_data["name"] = name_tag.get_text(strip=True)

        # try address
        addr_tag = soup.find("span", {"itemprop": "address"}) or soup.find("address")
        if addr_tag:
            return_data["address"] = addr_tag.get_text(separator=" ", strip=True)[:200]

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
            if title and "infobel" not in title.lower():
                return_data["og_title"] = title

        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return_data["description"] = og_desc["content"][:300]

        # extract country and carrier from JSON-LD or meta
        country_m = re.search(r'"addressCountry"\s*:\s*"([^"]+)"', html)
        if country_m:
            return_data["country"] = country_m.group(1)

        # line type
        linetype_m = re.search(r'(?:mobile|landline|voip)', html, re.IGNORECASE)
        if linetype_m:
            return_data["line_type"] = linetype_m.group(0).lower()

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = infobel_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
