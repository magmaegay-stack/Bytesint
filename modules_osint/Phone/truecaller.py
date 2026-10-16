import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")

# Country code → ISO2 for Truecaller search URL
def _get_region(phone_e164: str) -> str:
    try:
        import phonenumbers
        pn = phonenumbers.parse(phone_e164, None)
        region = phonenumbers.region_code_for_number(pn)
        return region.lower() if region else "us"
    except Exception:
        return "us"


def truecaller_lookup(phone: str) -> dict:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "truecaller",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    phone_digits = clean.lstrip("+")
    region = _get_region(clean)

    try:
        s = requests.Session(impersonate="chrome120")

        resp = s.get(
            f"https://www.truecaller.com/search/{region}/{phone_digits}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.truecaller.com/",
            },
            timeout=20,
            allow_redirects=True,
        )

        if resp.status_code not in (200, 301, 302):
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        return_data = {"phone": clean}

        # ── JSON-LD structured data (most reliable) ───────────────────────────
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0]
                if not isinstance(data, dict):
                    continue
                name = data.get("name", "")
                generic = {"truecaller", "phone number lookup", "reverse phone lookup", ""}
                if name.strip().lower() not in generic:
                    return_data["caller_name"] = name.strip()

                if data.get("address"):
                    addr = data["address"]
                    if isinstance(addr, dict):
                        parts = [addr.get("addressLocality"), addr.get("addressRegion"),
                                 addr.get("addressCountry")]
                        return_data["address"] = ", ".join(p for p in parts if p)
                    else:
                        return_data["address"] = str(addr)

                if data.get("telephone"):
                    return_data["formatted_phone"] = data["telephone"]
                if data.get("description"):
                    return_data["description"] = data["description"][:200]
            except Exception:
                pass

        # ── embedded JSON data blocks ─────────────────────────────────────────
        for pattern in [
            r'"name"\s*:\s*"([^"]{2,60})"',
            r'"caller_name"\s*:\s*"([^"]{2,60})"',
        ]:
            if not return_data.get("caller_name"):
                m = re.search(pattern, html)
                if m:
                    candidate = m.group(1).strip()
                    generic = {"truecaller", "phone number", "undefined", "null", ""}
                    if candidate.lower() not in generic and not candidate.startswith("http"):
                        return_data["caller_name"] = candidate

        # ── operator / carrier ────────────────────────────────────────────────
        for pat in [r'"operator"\s*:\s*"([^"]+)"', r'"carrier"\s*:\s*"([^"]+)"',
                    r'(?:Operator|Carrier|Network)[:\s]+<[^>]*>([^<]+)<']:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return_data["operator"] = m.group(1).strip()
                break

        # ── line type ─────────────────────────────────────────────────────────
        for pat in [r'"lineType"\s*:\s*"([^"]+)"', r'"line_type"\s*:\s*"([^"]+)"',
                    r'(?:Line\s*Type|Type)[:\s]+<[^>]*>([^<]+)<']:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return_data["line_type"] = m.group(1).strip()
                break

        # ── country / region ──────────────────────────────────────────────────
        for pat in [r'"country"\s*:\s*"([^"]+)"', r'"countryCode"\s*:\s*"([^"]+)"',
                    r'Country[:\s]+<[^>]*>([^<]+)<']:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return_data["country"] = m.group(1).strip()
                break

        # ── spam score ────────────────────────────────────────────────────────
        spam_m = re.search(r'"spamScore"\s*[=:]\s*["\']?([\d.]+)', html)
        if spam_m:
            return_data["spam_score"] = float(spam_m.group(1))

        # ── report count ──────────────────────────────────────────────────────
        rep_m = re.search(r'(\d+)\s+(?:users?\s+)?(?:reported?|marked\s+spam|complaint)', html, re.IGNORECASE)
        if rep_m:
            return_data["reports_count"] = int(rep_m.group(1))

        # ── search count ─────────────────────────────────────────────────────
        search_m = re.search(r'(\d[\d,]*)\s+(?:time|search)', html, re.IGNORECASE)
        if search_m:
            return_data["search_count"] = search_m.group(1).replace(",", "")

        # ── city ──────────────────────────────────────────────────────────────
        city_m = re.search(r'"city"\s*:\s*"([^"]+)"', html)
        if city_m:
            return_data["city"] = city_m.group(1).strip()

        # ── tags / categories ─────────────────────────────────────────────────
        tags_m = re.search(r'"tags"\s*:\s*\[([^\]]+)\]', html)
        if tags_m:
            tags = re.findall(r'"([^"]{2,40})"', tags_m.group(1))
            if tags:
                return_data["tags"] = tags[:5]

        # enrich with phonenumbers library
        try:
            import phonenumbers
            from phonenumbers import geocoder, carrier as ph_carrier
            pn = phonenumbers.parse(clean, None)
            if not return_data.get("operator"):
                c = ph_carrier.name_for_number(pn, "en")
                if c:
                    return_data["operator"] = c
            if not return_data.get("country"):
                return_data["country"] = phonenumbers.region_code_for_number(pn)
            if not return_data.get("line_type"):
                nt = phonenumbers.number_type(pn)
                type_map = {
                    phonenumbers.PhoneNumberType.MOBILE: "mobile",
                    phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
                    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
                    phonenumbers.PhoneNumberType.VOIP: "voip",
                    phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
                    phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
                }
                return_data["line_type"] = type_map.get(nt, "unknown")
            location = geocoder.description_for_number(pn, "en")
            if location and not return_data.get("location"):
                return_data["location"] = location
        except Exception:
            pass

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v is not None and v != ""}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = truecaller_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
