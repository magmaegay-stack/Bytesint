import json
import os
import re
import sys
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def opencnam_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "opencnam",
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

        # Determine country region for Truecaller URL
        region = "us"
        try:
            import phonenumbers
            pn = phonenumbers.parse(clean, None)
            region = (phonenumbers.region_code_for_number(pn) or "us").lower()
        except Exception:
            pass

        # Caller ID lookup via Truecaller (region-aware URL)
        resp = requests.get(
            f"https://www.truecaller.com/search/{region}/{phone_clean}",
            headers={
                **headers,
                "Accept": "text/html,application/xhtml+xml",
            },
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Detect generic/homepage titles — means no data for this number
            GENERIC_FRAGMENTS = (
                "free reverse", "truecaller", "reverse phone", "phone number lookup",
                "lookup by truecaller",
            )

            og_title = soup.find("meta", property="og:title")
            title_raw = (og_title.get("content") if og_title else "") or \
                        (soup.find("title").get_text(strip=True) if soup.find("title") else "")

            title_lo = title_raw.lower()
            is_generic = any(frag in title_lo for frag in GENERIC_FRAGMENTS)

            if not is_generic and title_raw:
                # Title contains a specific caller name
                # Remove trailing "| Truecaller" or "- Phone Number Details"
                name = re.sub(r'\s*[-–|]\s*(?:Truecaller|Phone.*$)', '', title_raw, flags=re.IGNORECASE).strip()
                if name and len(name) > 2:
                    return_data["caller_name"] = name

            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = og_desc["content"]
                if "450 million" not in desc and "free reverse" not in desc.lower():
                    return_data["description"] = desc[:200]

            if return_data.get("caller_name"):
                result["result"] = "found"
                result["return"] = {k: v for k, v in return_data.items() if v}
            else:
                result["result"] = "not_found"
                result["return"] = {"status": "no_caller_name_found"}
                return result
        else:
            # try alternative: freecarrierlookup.com
            resp2 = requests.get(
                f"https://freecarrierlookup.com/api_request.php?phone={phone_clean}&apikey=",
                headers=headers,
                impersonate="chrome120",
                timeout=10,
            )
            if resp2.status_code == 200:
                try:
                    data = resp2.json()
                    if data.get("carrier"):
                        return_data["carrier"] = data["carrier"]
                    if data.get("isMobile") is not None:
                        return_data["is_mobile"] = data["isMobile"]
                    result["result"] = "found"
                    result["return"] = {k: v for k, v in return_data.items() if v is not None}
                    return result
                except Exception:
                    pass
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
    _res = opencnam_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
