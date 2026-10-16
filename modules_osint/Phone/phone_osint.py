import json
import os
import re
import sys
import io
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

if os.name == "nt":
    os.system("chcp 65001 >nul")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# allow imports from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phonenumbers
from phonenumbers import geocoder as ph_geocoder
from phonenumbers import carrier as ph_carrier
from phonenumbers import timezone as ph_timezone

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

from numinfo import numinfo_lookup
from carrier import carrier_lookup
from hlrlookup import hlrlookup_lookup
from opencnam import opencnam_lookup
from phonebook import phonebook_lookup
from osintphone import osintphone_lookup
from whatsapp import whatsapp_lookup
from telegram import telegram_lookup


def _clean_phone(phone: str) -> str:
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean
    return clean


# ──────────────────────────────────────────────────────────────────────────────
# Local phonenumbers library — offline, always reliable
# ──────────────────────────────────────────────────────────────────────────────

def lookup_phonenumbers_lib(phone: str) -> dict:
    """Parse and validate using libphonenumber (offline)."""
    clean = _clean_phone(phone)
    out = {"service": "phonenumbers_lib", "registered": False}
    try:
        pn = phonenumbers.parse(clean, None)
        if not phonenumbers.is_valid_number(pn):
            out["valid"] = False
            return out

        out["valid"] = True
        out["registered"] = True

        nt = phonenumbers.number_type(pn)
        type_map = {
            phonenumbers.PhoneNumberType.MOBILE: "mobile",
            phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
            phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
            phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
            phonenumbers.PhoneNumberType.VOIP: "voip",
            phonenumbers.PhoneNumberType.PAGER: "pager",
            phonenumbers.PhoneNumberType.SHARED_COST: "shared_cost",
            phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "personal",
            phonenumbers.PhoneNumberType.UAN: "uan",
            phonenumbers.PhoneNumberType.VOICEMAIL: "voicemail",
            phonenumbers.PhoneNumberType.UNKNOWN: "unknown",
        }
        out["line_type"] = type_map.get(nt, "unknown")

        region = phonenumbers.region_code_for_number(pn)
        if region:
            out["country_code"] = region

        location = ph_geocoder.description_for_number(pn, "en")
        if location:
            out["location"] = location

        carrier_name = ph_carrier.name_for_number(pn, "en")
        if carrier_name:
            out["carrier"] = carrier_name

        timezones = ph_timezone.time_zones_for_number(pn)
        if timezones:
            out["timezones"] = list(timezones)

        out["national_format"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.NATIONAL)
        out["international_format"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        out["e164_format"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)
        out["country_calling_code"] = pn.country_code
        out["national_number"] = pn.national_number

    except phonenumbers.NumberParseException as e:
        out["error"] = str(e)
        out["valid"] = False
    except Exception as e:
        out["error"] = str(e)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Truecaller — caller name, spam data
# ──────────────────────────────────────────────────────────────────────────────

def lookup_truecaller(phone: str) -> dict:
    """Truecaller search (undocumented public endpoint)."""
    clean = _clean_phone(phone)
    phone_digits = clean.lstrip("+")
    out = {"service": "truecaller", "registered": False}
    try:
        s = cffi_requests.Session(impersonate="chrome120")

        # First get a countryCode from prefix
        country_code = "US"
        try:
            pn = phonenumbers.parse(clean, None)
            region = phonenumbers.region_code_for_number(pn)
            if region:
                country_code = region
        except Exception:
            pass

        # Truecaller widget endpoint (no auth needed)
        r = s.get(
            f"https://www.truecaller.com/search/{country_code.lower()}/{phone_digits}",
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.truecaller.com/",
            },
            timeout=15,
            allow_redirects=True,
        )

        if r.status_code == 200:
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            # Try JSON-LD structured data
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict):
                        if data.get("name"):
                            name = data["name"]
                            if name.lower() not in ("truecaller", ""):
                                out["name"] = name
                                out["registered"] = True
                        if data.get("address"):
                            out["address"] = str(data["address"])
                        if data.get("description"):
                            out["description"] = data["description"][:200]
                except Exception:
                    pass

            # Try og:title
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"]
                # Filter generic Truecaller titles
                if not any(kw in title.lower() for kw in ("truecaller", "reverse", "lookup", "phone number")):
                    if not out.get("name"):
                        out["name"] = title.strip()
                        out["registered"] = True

            # Try main content h1
            h1 = soup.find("h1")
            if h1:
                name = h1.get_text(strip=True)
                if name and not any(kw in name.lower() for kw in ("truecaller", "reverse", "lookup")):
                    if not out.get("name"):
                        out["name"] = name
                        out["registered"] = True

            # Spam score
            spam_m = re.search(r'"spamScore"\s*[=:]\s*["\']?([\d.]+)', html)
            if spam_m:
                out["spam_score"] = float(spam_m.group(1))

            # Report count
            rep_m = re.search(r'(\d+)\s+(?:users?\s+)?(?:reported?|marked)', html, re.IGNORECASE)
            if rep_m:
                out["reports_count"] = int(rep_m.group(1))

        elif r.status_code == 404:
            out["registered"] = False
        elif r.status_code == 429:
            out["rate_limited"] = True

    except Exception as e:
        out["error"] = str(e)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# CallerID.com
# ──────────────────────────────────────────────────────────────────────────────

def lookup_callerid(phone: str) -> dict:
    """callerID.com reverse lookup — name & spam data."""
    phone_digits = _clean_phone(phone).lstrip("+")
    out = {"service": "callerid", "registered": False}
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://www.callerid.com/reverse-phone-lookup/{phone_digits}/",
            headers={
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=15,
            allow_redirects=True,
        )
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")

            h1 = soup.find("h1")
            if h1:
                name = h1.get_text(strip=True)
                bad_names = {"reverse phone lookup", "callerid.com", "phone lookup", ""}
                if name and name.lower() not in bad_names:
                    out["caller_name"] = name
                    out["registered"] = True

            spam_m = re.search(r'"spamScore"\s*:\s*(\d+)', r.text)
            if spam_m:
                out["spam_score"] = int(spam_m.group(1))

            desc = soup.find("meta", attrs={"name": "description"})
            if desc and desc.get("content"):
                content = desc["content"]
                if "phone number details" not in content.lower():
                    out["description"] = content[:200]

    except Exception as e:
        out["error"] = str(e)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Viber registration check
# ──────────────────────────────────────────────────────────────────────────────

def lookup_viber(phone: str) -> dict:
    """Check Viber registration via invite link."""
    clean = _clean_phone(phone)
    phone_digits = clean.lstrip("+")
    out = {"service": "viber", "registered": False}
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://invite.viber.com/?g2=AAAAAA&number=%2B{phone_digits}",
            headers={"Accept": "text/html"},
            timeout=12,
            allow_redirects=True,
        )
        if r.status_code == 200:
            html = r.text
            if "viber://" in html.lower() or "open viber" in html.lower():
                out["registered"] = True
                out["invite_url"] = f"viber://add?number=%2B{phone_digits}"
    except Exception as e:
        out["error"] = str(e)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Spam reports: spamcalls.net
# ──────────────────────────────────────────────────────────────────────────────

def lookup_spamcalls(phone: str) -> dict:
    """Spam/scam reports from spamcalls.net."""
    phone_digits = _clean_phone(phone).lstrip("+")
    out = {"service": "spamcalls", "registered": False}
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://spamcalls.net/en/search/{phone_digits}",
            headers={"Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"},
            timeout=15,
            allow_redirects=True,
        )
        if r.status_code == 200:
            count_m = re.search(r'(\d+)\s+(?:report|comment|call)', r.text, re.IGNORECASE)
            if count_m:
                out["reports_count"] = int(count_m.group(1))
                out["registered"] = True
            rating_m = re.search(r'"ratingValue"\s*[=:]\s*"?([\d.]+)"?', r.text)
            if rating_m:
                out["rating"] = float(rating_m.group(1))
    except Exception as e:
        out["error"] = str(e)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Number reputation: shouldianswer.com
# ──────────────────────────────────────────────────────────────────────────────

def lookup_shouldianswer(phone: str) -> dict:
    """Should I Answer — community spam ratings."""
    phone_digits = _clean_phone(phone).lstrip("+")
    out = {"service": "shouldianswer", "registered": False}
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://www.shouldianswer.net/phone-number/{phone_digits}",
            headers={"Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"},
            timeout=15,
            allow_redirects=True,
        )
        if r.status_code == 200:
            rating_m = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', r.text)
            if rating_m:
                out["safety_rating"] = float(rating_m.group(1))
                out["registered"] = True
            count_m = re.search(r'"ratingCount"\s*:\s*"?(\d+)"?', r.text)
            if count_m:
                out["rating_count"] = int(count_m.group(1))
            # category/username
            cat_m = re.search(r'"category"\s*:\s*"([^"]+)"', r.text)
            if cat_m:
                out["category"] = cat_m.group(1)
    except Exception as e:
        out["error"] = str(e)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Merge helpers
# ──────────────────────────────────────────────────────────────────────────────

def _merge_number_info(*sources) -> dict:
    info = {}
    priority_keys = [
        "country", "country_code", "country_calling_code",
        "carrier", "line_type", "location", "timezones",
        "area_code", "local_number", "national_format", "international_format",
        "is_ported", "is_roaming", "network_type", "mccmnc",
    ]
    for src in sources:
        r = src.get("return", {}) if "return" in src else src
        for key in priority_keys:
            if key not in info or not info.get(key):
                val = r.get(key)
                if val is not None and val not in ("", "verified"):
                    info[key] = val
    return info


# ──────────────────────────────────────────────────────────────────────────────
# Main aggregator
# ──────────────────────────────────────────────────────────────────────────────

def phone_osint(phone: str) -> dict:
    clean = _clean_phone(phone)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    output = {
        "phone": clean,
        "generated": generated,
        "number_info": {},
        "caller_id": {},
        "reputation": {},
        "registered_services": {},
        "raw": {},
        "summary": {},
    }

    tasks = {
        "phonenumbers":   lambda: lookup_phonenumbers_lib(clean),
        "numinfo":        lambda: numinfo_lookup(clean),
        "carrier":        lambda: carrier_lookup(clean),
        "hlrlookup":      lambda: hlrlookup_lookup(clean),
        "opencnam":       lambda: opencnam_lookup(clean),
        "truecaller":     lambda: lookup_truecaller(clean),
        "callerid":       lambda: lookup_callerid(clean),
        "phonebook":      lambda: phonebook_lookup(clean),
        "osintphone":     lambda: osintphone_lookup(clean),
        "shouldianswer":  lambda: lookup_shouldianswer(clean),
        "spamcalls":      lambda: lookup_spamcalls(clean),
        "whatsapp":       lambda: whatsapp_lookup(clean),
        "telegram":       lambda: telegram_lookup(clean),
        "viber":          lambda: lookup_viber(clean),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fn): name for name, fn in tasks.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                results[name] = fut.result()
            except Exception as e:
                results[name] = {"error": str(e)}

    output["raw"] = results

    # ── number_info ───────────────────────────────────────────────────────────
    info_sources = [results.get(k, {}) for k in ("phonenumbers", "numinfo", "carrier",
                                                   "hlrlookup")]
    output["number_info"] = _merge_number_info(*info_sources)

    # also pick up carrier from hlrlookup return
    hlr_ret = results.get("hlrlookup", {}).get("return", {})
    for key in ("operator", "network_type", "is_ported", "is_roaming"):
        if key not in output["number_info"] or not output["number_info"].get(key):
            val = hlr_ret.get(key)
            if val is not None:
                output["number_info"][key] = val
    if hlr_ret.get("operator") and not output["number_info"].get("carrier"):
        output["number_info"]["carrier"] = hlr_ret["operator"]

    # ── caller_id ─────────────────────────────────────────────────────────────
    _generic_names = {
        "free reverse phone number lookup by truecaller",
        "truecaller", "reverse phone lookup", "phone number lookup",
        "callerid.com", "spydialer", "unknown",
    }

    for src_name in ("truecaller", "callerid", "opencnam", "phonebook"):
        src = results.get(src_name, {})
        r = src.get("return", src)
        name_val = r.get("name") or r.get("caller_name")
        if name_val and name_val.strip().lower() not in _generic_names:
            if not output["caller_id"].get("name"):
                output["caller_id"]["name"] = name_val.strip()
                output["caller_id"]["source"] = src_name

        if not output["caller_id"].get("address"):
            loc = r.get("location") or r.get("address")
            if loc:
                output["caller_id"]["address"] = loc

        if not output["caller_id"].get("spam_score"):
            score = r.get("spam_score")
            if score is not None:
                output["caller_id"]["spam_score"] = score

    # ── reputation ────────────────────────────────────────────────────────────
    rep = {}
    for src_name in ("osintphone", "shouldianswer", "spamcalls", "truecaller", "callerid"):
        src = results.get(src_name, {})
        r = src.get("return", src)

        if r.get("reports_count") is not None and rep.get("report_count") is None:
            rep["report_count"] = r["reports_count"]
        if r.get("safety_rating") is not None and rep.get("safety_rating") is None:
            rep["safety_rating"] = r["safety_rating"]
        if r.get("spam_score") is not None and rep.get("spam_score") is None:
            rep["spam_score"] = r["spam_score"]
        if r.get("rating_count") is not None and rep.get("rating_count") is None:
            rep["rating_count"] = r["rating_count"]
        if r.get("category") and not rep.get("category"):
            rep["category"] = r["category"]
        if r.get("notes_summary") and not rep.get("notes"):
            rep["notes"] = r["notes_summary"]
        if r.get("usernames") and not rep.get("usernames"):
            rep["usernames"] = r["usernames"]
    output["reputation"] = rep

    # ── registered_services ───────────────────────────────────────────────────
    services = {}

    wa = results.get("whatsapp", {})
    wa_r = wa.get("return", {})
    services["whatsapp"] = {"registered": wa.get("result") == "found"}
    if wa_r.get("display_name"):
        services["whatsapp"]["display_name"] = wa_r["display_name"]
    if wa_r.get("click_to_chat_url"):
        services["whatsapp"]["url"] = wa_r["click_to_chat_url"]

    tg = results.get("telegram", {})
    tg_r = tg.get("return", {})
    services["telegram"] = {"registered": tg.get("result") == "found"}
    if tg_r.get("status"):
        services["telegram"]["status"] = tg_r["status"]
    if tg_r.get("note"):
        services["telegram"]["note"] = tg_r["note"]

    vb = results.get("viber", {})
    services["viber"] = {"registered": vb.get("registered", False)}
    if vb.get("invite_url"):
        services["viber"]["url"] = vb["invite_url"]

    output["registered_services"] = services

    # ── summary ───────────────────────────────────────────────────────────────
    registered = [k for k, v in services.items() if v.get("registered")]
    errors = [k for k, v in results.items() if v.get("error") or v.get("result") == "error"]
    rate_limited = [k for k, v in results.items() if v.get("rate_limited")]

    output["summary"] = {
        "total_lookups": len(tasks),
        "errors": len(errors),
        "rate_limited": len(rate_limited),
        "registered_services": registered,
        "caller_name": output["caller_id"].get("name"),
        "country": output["number_info"].get("country"),
        "country_code": output["number_info"].get("country_code"),
        "carrier": output["number_info"].get("carrier"),
        "line_type": output["number_info"].get("line_type"),
        "location": output["number_info"].get("location"),
        "spam_reports": rep.get("report_count", 0),
        "valid_number": results.get("phonenumbers", {}).get("valid"),
    }
    output["summary"] = {k: v for k, v in output["summary"].items() if v is not None}

    # remove empty sections
    for section in ("number_info", "caller_id", "reputation"):
        if not output.get(section):
            output.pop(section, None)

    return output


# ──────────────────────────────────────────────────────────────────────────────
# Human-readable output
# ──────────────────────────────────────────────────────────────────────────────

def print_human(data: dict) -> None:
    phone = data.get("phone", "?")
    gen = data.get("generated", "")
    summary = data.get("summary", {})
    number_info = data.get("number_info", {})
    caller_id = data.get("caller_id", {})
    reputation = data.get("reputation", {})
    services = data.get("registered_services", {})

    print(f"\n{'='*62}")
    print(f"  PHONE OSINT — {phone}")
    print(f"  {gen}")
    print(f"{'='*62}")

    if number_info:
        print("\n[NUMBER INFO]")
        for k, v in number_info.items():
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            print(f"  {k:<26}: {v}")

    if caller_id:
        print("\n[CALLER ID]")
        for k, v in caller_id.items():
            print(f"  {k:<26}: {v}")

    if reputation:
        print("\n[REPUTATION]")
        for k, v in reputation.items():
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            print(f"  {k:<26}: {v}")

    if services:
        print("\n[REGISTERED SERVICES]")
        for svc, info in services.items():
            reg = info.get("registered")
            status = "FOUND    " if reg is True else ("UNKNOWN  " if reg is None else "NOT FOUND")
            extra = ""
            for key in ("display_name", "note", "url", "status"):
                val = info.get(key)
                if val:
                    extra = f" — {val}"
                    break
            print(f"  {svc:<12} {status}{extra}")

    if summary:
        print("\n[SUMMARY]")
        for k, v in summary.items():
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v) if v else "none"
            print(f"  {k:<26}: {v}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phone OSINT master module")
    parser.add_argument("phone", help="Phone number with country code (e.g. +39340XXXXXXX)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    result = phone_osint(args.phone)

    if args.json:
        sys.stdout.write(json.dumps(result, indent=4, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        os._exit(0)
    else:
        print_human(result)
        sys.stdout.flush()
        os._exit(0)
