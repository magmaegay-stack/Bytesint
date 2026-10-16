import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def hlrlookup_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "hlrlookup",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    return_data = {"phone": clean}

    # Primary: phonenumbers library (offline, always reliable)
    try:
        import phonenumbers
        from phonenumbers import carrier as ph_carrier, geocoder, number_type, PhoneNumberType

        pn = phonenumbers.parse(clean, None)
        if phonenumbers.is_valid_number(pn):
            return_data["valid"] = True

            carrier_name = ph_carrier.name_for_number(pn, "en")
            if carrier_name:
                return_data["carrier"] = carrier_name

            country_desc = geocoder.description_for_number(pn, "en")
            if country_desc:
                return_data["country"] = country_desc

            region = phonenumbers.region_code_for_number(pn)
            if region:
                return_data["country_code"] = region

            ntype = number_type(pn)
            type_map = {
                PhoneNumberType.MOBILE: "mobile",
                PhoneNumberType.FIXED_LINE: "landline",
                PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
                PhoneNumberType.VOIP: "voip",
                PhoneNumberType.TOLL_FREE: "toll_free",
                PhoneNumberType.PREMIUM_RATE: "premium_rate",
            }
            ntype_str = type_map.get(ntype)
            if ntype_str:
                return_data["network_type"] = ntype_str

            result["result"] = "found"
        else:
            return_data["valid"] = False
            result["result"] = "not_found"
            result["return"] = return_data
            return result
    except Exception:
        pass

    # Supplement: freecarrierlookup.com (may give ported/roaming info)
    try:
        phone_clean = clean.lstrip("+")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        resp = requests.get(
            f"https://freecarrierlookup.com/?phone={phone_clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for row in soup.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    val = cells[1].get_text(strip=True)
                    if not val or val in ("-", "N/A", "n/a"):
                        continue
                    if "carrier" in key and not return_data.get("carrier"):
                        return_data["carrier"] = val
                    elif "type" in key and not return_data.get("network_type"):
                        return_data["network_type"] = val.lower()
                    elif "ported" in key:
                        return_data["is_ported"] = val.lower() in ("yes", "true", "1")
                    elif "roaming" in key:
                        return_data["is_roaming"] = val.lower() in ("yes", "true", "1")
                    elif "country" in key and not return_data.get("country"):
                        return_data["country"] = val
    except Exception:
        pass

    result["return"] = {k: v for k, v in return_data.items() if v is not None and v != ""}
    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = hlrlookup_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
