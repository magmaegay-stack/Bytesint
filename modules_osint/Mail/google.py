#!/usr/bin/env python3
"""
google_osint.py — recon OSINT su account Google da email.

Dato EMAIL + cookies.txt ritorna:
    - registered, gaia_id, name, profile_photo, cover_photo
    - email_verified, user_types, services, last_edit, emails_found

Setup:
    pip install requests

Cookies:
    1. loggati in un account burner Google (incognito)
    2. visita https://photos.google.com/
    3. esporta cookie .google.com in formato Netscape → cookies.txt
       (estensione "Get cookies.txt LOCALLY")

Uso:
    python google_osint.py target@gmail.com --cookies cookies.txt
    python google_osint.py target@gmail.com --cookies cookies.txt --json
"""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

import requests

log = logging.getLogger("gosint")

PEOPLE_LOOKUP = "https://people-pa.clients6.google.com/v2/people/lookup"
PEOPLE_BY_ID = "https://people-pa.clients6.google.com/v2/people"
PHOTOS_API_KEY = "AIzaSyAa2odBewW-sPJu3jMORr0aNedh3YlkiQc"
PHOTOS_ORIGIN = "https://photos.google.com"

UA = "Mozilla/5.0 (Windows NT 10.0; rv:68.0) Gecko/20100101 Firefox/68.0"


@dataclass
class GoogleRecon:
    email: str
    registered: Optional[bool] = None
    name: Optional[str] = None
    gaia_id: Optional[str] = None
    profile_photo: Optional[str] = None
    cover_photo: Optional[str] = None
    email_verified: Optional[bool] = None
    last_edit: Optional[str] = None
    user_types: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    emails_found: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------- auth ----------

def gen_sapisidhash(sapisid: str, origin: str) -> str:
    ts = str(int(time.time()))
    digest = hashlib.sha1(f"{ts} {sapisid} {origin}".encode()).hexdigest()
    return f"{ts}_{digest}"


def load_cookies(path: str) -> dict:
    cj = http.cookiejar.MozillaCookieJar(path)
    cj.load(ignore_discard=True, ignore_expires=True)
    return {c.name: c.value for c in cj if "google" in c.domain}


def _headers(sapisid: str) -> dict:
    return {
        "User-Agent": UA,
        "Connection": "Keep-Alive",
        "X-Goog-Api-Key": PHOTOS_API_KEY,
        "Origin": PHOTOS_ORIGIN,
        "Referer": PHOTOS_ORIGIN,
        "Authorization": f"SAPISIDHASH {gen_sapisidhash(sapisid, PHOTOS_ORIGIN)}",
    }


# ---------- API calls ----------

def api_lookup_by_email(email: str, cookies: dict, timeout: float = 20.0) -> dict:
    sapisid = cookies.get("SAPISID")
    if not sapisid:
        return {"error": "missing_SAPISID"}

    params = [
        ("id", email), ("type", "EMAIL"), ("match_type", "EXACT"),
        ("extension_set.extension_names", "DYNAMITE_ADDITIONAL_DATA"),
        ("extension_set.extension_names", "DYNAMITE_ORGANIZATION_INFO"),
        ("request_mask.include_field.paths", "person.metadata.best_display_name"),
        ("request_mask.include_field.paths", "person.photo"),
        ("request_mask.include_field.paths", "person.cover_photo"),
        ("request_mask.include_field.paths", "person.metadata"),
        ("request_mask.include_field.paths", "person.in_app_reachability"),
        ("request_mask.include_field.paths", "person.name"),
        ("request_mask.include_field.paths", "person.read_only_profile_info"),
        ("request_mask.include_field.paths", "person.email"),
        ("request_mask.include_container", "PROFILE"),
        ("request_mask.include_container", "DOMAIN_PROFILE"),
        ("request_mask.include_container", "CONTACT"),
        ("core_id_params.enable_private_names", "true"),
    ]

    try:
        r = requests.get(PEOPLE_LOOKUP, params=params, headers=_headers(sapisid),
                         cookies=cookies, timeout=timeout)
    except requests.RequestException as e:
        return {"error": f"network: {e}"}

    log.debug("lookup HTTP %d size=%d", r.status_code, len(r.text))
    if r.status_code >= 400:
        return {"error": f"http_{r.status_code}"}

    try:
        return {"response": r.json()}
    except ValueError:
        return {"error": "non_json"}


def api_lookup_by_gaia(gaia_id: str, cookies: dict, timeout: float = 20.0) -> dict:
    """
    Fallback: lookup diretto per GAIA id. A volte espone campi (name incluso)
    che il lookup by email patcha.
    """
    sapisid = cookies.get("SAPISID")
    if not sapisid:
        return {"error": "missing_SAPISID"}

    params = [
        ("person_id", gaia_id),
        ("extension_set.extension_names", "DYNAMITE_ADDITIONAL_DATA"),
        ("request_mask.include_field.paths", "person.metadata.best_display_name"),
        ("request_mask.include_field.paths", "person.name"),
        ("request_mask.include_field.paths", "person.read_only_profile_info"),
        ("core_id_params.enable_private_names", "true"),
    ]

    try:
        r = requests.get(PEOPLE_BY_ID, params=params, headers=_headers(sapisid),
                         cookies=cookies, timeout=timeout)
    except requests.RequestException as e:
        return {"error": f"network: {e}"}

    log.debug("gaia lookup HTTP %d size=%d", r.status_code, len(r.text))
    if r.status_code >= 400:
        return {"error": f"http_{r.status_code}"}

    try:
        return {"response": r.json()}
    except ValueError:
        return {"error": "non_json"}


# ---------- parser ----------

def _clean_name(candidate: Optional[str], email: str) -> Optional[str]:
    """Scarta nomi inutili: vuoti, uguali all'email, prefisso email."""
    if not candidate:
        return None
    n = str(candidate).strip()
    if not n:
        return None
    if n.lower() == email.lower():
        return None
    if "@" in n:
        return None
    local = email.split("@")[0].lower()
    if n.lower() == local:
        return None
    return n


def parse_person(data: dict, email: str) -> GoogleRecon:
    res = GoogleRecon(email=email)

    if not data or "people" not in data or not data["people"]:
        res.registered = False
        return res

    person_data = list(data["people"].values())[0]

    res.registered = True
    res.gaia_id = str(person_data.get("personId") or "")

    # name: bestDisplayName → name[] → scarta se è l'email
    best = (person_data.get("metadata", {}) or {}).get("bestDisplayName") or {}
    if isinstance(best, dict):
        res.name = _clean_name(best.get("displayName"), email)
    if not res.name:
        for n in person_data.get("name", []) or []:
            if isinstance(n, dict):
                cand = _clean_name(n.get("displayName") or n.get("displayNameLastFirst"), email)
                if cand:
                    res.name = cand
                    break

    # photo
    for photo in person_data.get("photo", []) or []:
        if isinstance(photo, dict):
            url = photo.get("url")
            if url and not res.profile_photo:
                res.profile_photo = url
                break

    # cover
    for cover in person_data.get("coverPhoto", []) or []:
        if isinstance(cover, dict):
            url = cover.get("imageUrl")
            if url and not res.cover_photo:
                parts = url.split("=")
                res.cover_photo = "=".join(parts[:-1]) if len(parts) > 1 else url
                break

    # emails + verified
    for em in person_data.get("email", []) or []:
        if isinstance(em, dict):
            val = em.get("value")
            if val and val not in res.emails_found:
                res.emails_found.append(val)
            if val and val.lower() == email.lower():
                v = (em.get("metadata") or {}).get("verified")
                if isinstance(v, bool):
                    res.email_verified = v

    # services
    seen = set()
    for app in person_data.get("inAppReachability", []) or []:
        if isinstance(app, dict):
            t = app.get("appType")
            if t and t not in seen:
                seen.add(t)
                res.services.append(str(t).title())

    # user types
    for prof in person_data.get("readOnlyProfileInfo", []) or []:
        if isinstance(prof, dict):
            for ut in prof.get("ownerUserType", []) or []:
                if ut and ut not in res.user_types:
                    res.user_types.append(str(ut))

    # last edit
    ids = ((person_data.get("metadata", {}) or {})
           .get("identityInfo", {}) or {}).get("sourceIds", []) or []
    for s in ids:
        if isinstance(s, dict):
            ts = s.get("lastUpdatedMicros")
            if ts:
                try:
                    res.last_edit = datetime.utcfromtimestamp(float(str(ts)[:10])).isoformat() + "Z"
                    break
                except Exception:
                    pass

    return res


def parse_name_from_gaia_response(data: dict, email: str) -> Optional[str]:
    """
    Response di /v2/people è {personResponse: [{status, person: {...}}]}
    """
    if not isinstance(data, dict):
        return None
    resps = data.get("personResponse", [])
    if not resps or not isinstance(resps, list):
        return None
    person = resps[0].get("person", {})
    if not isinstance(person, dict):
        return None

    best = (person.get("metadata", {}) or {}).get("bestDisplayName") or {}
    if isinstance(best, dict):
        n = _clean_name(best.get("displayName"), email)
        if n:
            return n

    for n in person.get("name", []) or []:
        if isinstance(n, dict):
            cand = _clean_name(n.get("displayName") or n.get("displayNameLastFirst"), email)
            if cand:
                return cand
    return None


# ---------- orchestrator ----------

def run_recon(email: str, cookies_file: str) -> GoogleRecon:
    cookies = load_cookies(cookies_file)
    if "SAPISID" not in cookies:
        res = GoogleRecon(email=email)
        res.errors.append("cookies.txt senza SAPISID — rigenera dopo aver visitato photos.google.com")
        return res

    r1 = api_lookup_by_email(email, cookies)
    if "error" in r1:
        res = GoogleRecon(email=email)
        res.errors.append(f"lookup: {r1['error']}")
        return res

    res = parse_person(r1["response"], email)

    # se name mancante e abbiamo GAIA, prova endpoint by-id
    if res.registered and not res.name and res.gaia_id:
        r2 = api_lookup_by_gaia(res.gaia_id, cookies)
        if "response" in r2:
            n = parse_name_from_gaia_response(r2["response"], email)
            if n:
                res.name = n

    return res


# ---------- output ----------

def print_human(r: GoogleRecon):
    if r.email_verified is not None:
        pass
    if r.last_edit:
        pass
    if r.user_types:
        pass
    if r.services:
        pass
    if r.emails_found:
        pass
    if r.errors:
        pass


def main():
    ap = argparse.ArgumentParser(description="OSINT Google da email")
    ap.add_argument("email", help="email target")
    ap.add_argument("--cookies", required=True, help="cookies.txt Netscape")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", args.email):
        sys.exit(2)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s %(message)s")

    try:
        res = run_recon(args.email, args.cookies)
    except FileNotFoundError:
        sys.exit(2)
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    if args.json:
        print(json.dumps(asdict(res), indent=2, ensure_ascii=False))
    else:
        print_human(res)

    sys.exit(0 if res.registered else 1)


if __name__ == "__main__":
    import sys as _sys
    from dataclasses import asdict as _asdict
    from pathlib import Path as _Path
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _cookies_path = str(_Path(__file__).parent / "cookies.txt")
    if not _Path(_cookies_path).exists():
        print('{"error": "cookies.txt not found — required for Google OSINT"}')
        _sys.exit(1)
    try:
        _res = run_recon(_sys.argv[1].strip(), _cookies_path)
        print(json.dumps(_asdict(_res), indent=4, ensure_ascii=False))
    except Exception as _e:
        print(json.dumps({"error": str(_e)}, indent=4, ensure_ascii=False))
