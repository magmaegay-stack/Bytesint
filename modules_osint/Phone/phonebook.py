import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def phonebook_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "phonebook",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    return_data = {"phone": clean}

    # Base: phonenumbers library for offline carrier/type/country
    try:
        import phonenumbers
        from phonenumbers import carrier as ph_carrier, geocoder, number_type, PhoneNumberType

        pn = phonenumbers.parse(clean, None)
        if phonenumbers.is_valid_number(pn):
            carrier_name = ph_carrier.name_for_number(pn, "en")
            if carrier_name:
                return_data["carrier"] = carrier_name

            country_desc = geocoder.description_for_number(pn, "en")
            if country_desc:
                return_data["country"] = country_desc

            ntype = number_type(pn)
            type_map = {
                PhoneNumberType.MOBILE: "mobile",
                PhoneNumberType.FIXED_LINE: "landline",
                PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
                PhoneNumberType.VOIP: "voip",
                PhoneNumberType.TOLL_FREE: "toll_free",
            }
            ntype_str = type_map.get(ntype)
            if ntype_str:
                return_data["line_type"] = ntype_str

            region = phonenumbers.region_code_for_number(pn)
            if region:
                return_data["country_code"] = region

            country_desc = geocoder.description_for_number(pn, "en")
            if country_desc:
                return_data["country"] = country_desc

            result["result"] = "found"
    except Exception:
        pass

    # Try callerinfo.com for caller name lookup
    try:
        phone_clean = clean.lstrip("+")
        resp = requests.get(
            f"https://www.callerinfo.com/lookup/{phone_clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for name in structured result containers
            name_tag = (
                soup.find(class_=re.compile(r"caller.?name|name.?result|owner.?name", re.IGNORECASE))
                or soup.find(id=re.compile(r"caller.?name|name.?result|owner", re.IGNORECASE))
            )
            if name_tag:
                name = name_tag.get_text(strip=True)
                if name and len(name) > 2 and "callerinfo" not in name.lower():
                    return_data["caller_name"] = name

            # Extract from JSON-LD only (avoid body text false positives)
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    ld = json.loads(script.string or "")
                    if isinstance(ld, dict):
                        if ld.get("name") and len(ld["name"]) > 2:
                            return_data["caller_name"] = ld["name"]
                        if ld.get("address"):
                            addr = ld["address"]
                            if isinstance(addr, dict):
                                parts = [addr.get("addressLocality", ""), addr.get("addressRegion", ""), addr.get("addressCountry", "")]
                                loc = ", ".join(p for p in parts if p)
                                if loc:
                                    return_data["location"] = loc
                except Exception:
                    pass

            result["result"] = "found"
    except Exception:
        pass

    # Try numlookup.com as second source for additional data
    try:
        phone_clean = clean.lstrip("+")
        resp2 = requests.get(
            f"https://www.numlookup.com/{clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        if resp2.status_code == 200:
            soup2 = BeautifulSoup(resp2.text, "html.parser")

            for row in soup2.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    val = cells[1].get_text(strip=True)
                    if not val or val in ("-", "N/A", "Unknown"):
                        continue
                    if "carrier" in key and not return_data.get("carrier"):
                        return_data["carrier"] = val
                    elif "type" in key and not return_data.get("line_type"):
                        return_data["line_type"] = val.lower()
                    elif "country" in key and not return_data.get("country"):
                        return_data["country"] = val
                    elif "city" in key or "location" in key:
                        if not return_data.get("location"):
                            return_data["location"] = val

            result["result"] = "found"
    except Exception:
        pass

    result["return"] = {k: v for k, v in return_data.items() if v is not None and v != ""}
    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = phonebook_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
