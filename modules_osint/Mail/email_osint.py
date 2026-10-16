#!/usr/bin/env python3
"""
email_osint.py — Full email OSINT (no API keys required).

Lookups:
  - Gravatar profile (name, avatar, bio, location, linked accounts)
  - EmailRep.io reputation (breach flag, deliverability, spam, services)
  - DNS/MX domain analysis
  - Service registration: GitHub, Spotify, Adobe, Steam, Skype/Microsoft,
                          Dropbox, Pinterest, Twitch, Tumblr, Discord

Usage:
    python email_osint.py target@example.com
    python email_osint.py target@example.com --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sys
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

from curl_cffi import requests as cffi_requests

if os.name == "nt":
    os.system("chcp 65001 >nul")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
IMPERSONATE = "chrome120"
TIMEOUT = 15


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _session() -> cffi_requests.Session:
    return cffi_requests.Session(impersonate=IMPERSONATE)


def _md5(s: str) -> str:
    return hashlib.md5(s.strip().lower().encode()).hexdigest()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.strip().lower().encode()).hexdigest()


def _get_mx(domain: str) -> list[str]:
    """Risolve MX records usando Google DNS (8.8.8.8) per bypassare DNS locali bloccati."""
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
        resolver.lifetime = 8.0
        answers = resolver.resolve(domain, "MX")
        return sorted([str(r.exchange).rstrip(".") for r in answers])
    except ImportError:
        pass
    except Exception:
        pass

    try:
        socket.getaddrinfo(domain, None)
        return [f"(A record only — MX lookup failed)"]
    except Exception:
        return []


# ─────────────────────────────────────────────
# LOOKUP 1: Gravatar
# ─────────────────────────────────────────────

def lookup_gravatar(email: str) -> dict:
    h = _md5(email)
    url = f"https://en.gravatar.com/{h}.json"
    out = {"found": False, "hash": h}
    try:
        r = cffi_requests.get(url, headers={"User-Agent": UA, "Accept": "application/json"},
                               impersonate=IMPERSONATE, timeout=TIMEOUT)
        if r.status_code != 200:
            return out
        entries = r.json().get("entry", [])
        if not entries:
            return out
        u = entries[0]
        out["found"] = True
        if u.get("displayName"):
            out["name"] = u["displayName"]
        if u.get("thumbnailUrl"):
            out["avatar"] = u["thumbnailUrl"]
        if u.get("aboutMe"):
            out["bio"] = u["aboutMe"]
        if u.get("currentLocation"):
            out["location"] = u["currentLocation"]
        if u.get("profileUrl"):
            out["profile_url"] = u["profileUrl"]
        accounts = u.get("accounts", [])
        if accounts:
            out["connected_accounts"] = [
                {"service": a.get("shortname"), "name": a.get("name"), "url": a.get("url")}
                for a in accounts
            ]
        urls = u.get("urls", [])
        if urls:
            out["websites"] = [{"title": x.get("title"), "url": x.get("value")} for x in urls]
        emails_json = u.get("emails", [])
        if emails_json:
            out["emails"] = [e.get("value") for e in emails_json if e.get("value")]
        ims = u.get("ims", [])
        if ims:
            out["ims"] = [{"type": x.get("type"), "value": x.get("value")} for x in ims]
    except Exception as e:
        out["error"] = str(e)
    return out


# ─────────────────────────────────────────────
# LOOKUP 2: EmailRep.io
# ─────────────────────────────────────────────

def lookup_emailrep(email: str) -> dict:
    out = {"found": False}
    try:
        r = cffi_requests.get(
            f"https://emailrep.io/{email}",
            headers={"User-Agent": "email-osint/1.0", "Accept": "application/json"},
            impersonate=IMPERSONATE,
            timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        if r.status_code != 200:
            return out
        data = r.json()
        if not data or data.get("status") == "fail":
            return out
        out["found"] = True
        attrs = data.get("details", {}) or {}
        if data.get("reputation"):
            out["reputation"] = data["reputation"]
        for key in ("suspicious", "blacklisted", "credentials_leaked", "data_breach",
                    "spam", "free_provider", "disposable", "deliverable", "smtp_valid",
                    "spoofable", "spf_strict", "dmarc_enforced"):
            if key in attrs:
                out[key] = attrs[key]
        if attrs.get("first_seen"):
            out["first_seen"] = attrs["first_seen"]
        if attrs.get("last_seen"):
            out["last_seen"] = attrs["last_seen"]
        if isinstance(attrs.get("references"), int):
            out["references"] = attrs["references"]
        profiles = attrs.get("profiles", [])
        if profiles:
            out["profiles"] = profiles
        if attrs.get("domain_reputation"):
            out["domain_reputation"] = attrs["domain_reputation"]
        if attrs.get("domain_exists") is not None:
            out["domain_exists"] = attrs["domain_exists"]
        if attrs.get("mx_records") is not None:
            out["mx_records"] = attrs["mx_records"]
        if attrs.get("valid_mx") is not None:
            out["valid_mx"] = attrs["valid_mx"]
    except Exception as e:
        out["error"] = str(e)
    return out


# ─────────────────────────────────────────────
# LOOKUP 3: Domain / DNS
# ─────────────────────────────────────────────

def lookup_domain(email: str) -> dict:
    domain = email.split("@")[-1].lower()
    out = {"domain": domain}
    mx = _get_mx(domain)
    if mx:
        out["mx_records"] = mx
    try:
        ips = list({r[4][0] for r in socket.getaddrinfo(domain, None)})
        out["a_records"] = ips
    except Exception:
        out["a_records"] = []
    return out


# ─────────────────────────────────────────────
# LOOKUP 4: GitHub
# ─────────────────────────────────────────────

def lookup_github(email: str) -> dict:
    out = {"registered": None, "rate_limited": False}
    s = _session()
    headers = {
        "User-Agent": UA, "Accept": "application/json",
        "Origin": "https://github.com", "Referer": "https://github.com/password_reset",
    }
    try:
        page = s.get("https://github.com/password_reset", headers=headers, timeout=TIMEOUT)
        token_m = re.search(r'name="authenticity_token"[^>]*value="([^"]+)"', page.text)
        token = token_m.group(1) if token_m else ""

        check = s.post(
            "https://github.com/signup_check/email",
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded",
                     "X-Requested-With": "XMLHttpRequest"},
            data={"authenticity_token": token, "value": email.strip()},
            timeout=TIMEOUT,
        )
        if check.status_code == 429:
            out["rate_limited"] = True
            return out
        if check.status_code == 422:
            out["registered"] = True
            return out
        if check.status_code == 200:
            try:
                cj = check.json()
                if cj.get("errors") or "taken" in str(cj).lower():
                    out["registered"] = True
                else:
                    out["registered"] = False
            except Exception:
                out["registered"] = False
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# LOOKUP 5: Spotify
# ─────────────────────────────────────────────

def lookup_spotify(email: str) -> dict:
    import uuid
    out = {"registered": None, "rate_limited": False}
    payload = {
        "fields": [{"field": "FIELD_EMAIL", "value": email.strip()}],
        "client_info": {
            "api_key": "a1e486e2729f46d6bb368d6b2bcda326",
            "app_version": "v2", "capabilities": [1],
            "installation_id": str(uuid.uuid4()), "platform": "www", "client_id": "",
        },
        "tracking": {"creation_flow": "", "creation_point": "https://www.spotify.com/signup/",
                     "referrer": "", "origin_vertical": "", "origin_surface": ""},
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Content-Type": "application/json", "Origin": "https://www.spotify.com",
        "Referer": "https://www.spotify.com/",
    }
    try:
        r = cffi_requests.post(
            "https://spclient.wg.spotify.com/signup/public/v2/account/validate",
            headers=headers, json=payload, impersonate=IMPERSONATE, timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        data = r.json() if r.status_code < 500 else {}
        error = data.get("error", {})
        if isinstance(error, dict):
            if "ALREADY_EXISTS" in str(error) or error.get("already_exists"):
                out["registered"] = True
                return out
            if error:
                out["registered"] = False
                return out
        if data.get("ok") is not None or r.status_code == 200:
            out["registered"] = False
    except Exception as e:
        out["error"] = str(e)
    return out


# ─────────────────────────────────────────────
# LOOKUP 6: Adobe
# ─────────────────────────────────────────────

def lookup_adobe(email: str) -> dict:
    out = {"registered": None, "rate_limited": False, "extra": {}}
    s = cffi_requests.Session(impersonate="chrome")
    headers = {
        "User-Agent": UA, "Accept": "application/json, text/plain, */*",
        "X-IMS-CLIENTID": "adobedotcom2",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://auth.services.adobe.com",
        "Referer": "https://auth.services.adobe.com/",
    }
    try:
        # Step 1: get auth state
        r1 = s.post(
            "https://auth.services.adobe.com/signin/v1/authenticationstate",
            headers=headers,
            json={"username": email.strip(), "accountType": "individual"},
            timeout=TIMEOUT,
        )
        if r1.status_code == 429:
            out["rate_limited"] = True
            return out
        state = r1.json()
        if "errorCode" in state:
            out["registered"] = False
            return out

        # Use the encrypted state header for step 2
        enc = (r1.headers.get("x-ims-authentication-state-encrypted") or
               r1.headers.get("X-IMS-Authentication-State-Encrypted"))
        if enc:
            headers["X-IMS-Authentication-State-Encrypted"] = enc

        # Step 2: get recovery challenges
        r2 = s.get(
            "https://auth.services.adobe.com/signin/v2/challenges",
            headers=headers,
            params={"purpose": "passwordRecovery"},
            timeout=TIMEOUT,
        )
        challenges = r2.json() if r2.status_code < 500 else {}
        out["registered"] = True

        sec_email = challenges.get("secondaryEmail")
        if sec_email:
            out["extra"]["recovery_email"] = sec_email
        phone = challenges.get("securityPhoneNumber")
        if phone:
            out["extra"]["recovery_phone"] = phone
        factors = challenges.get("availableFactors", [])
        if factors:
            out["extra"]["mfa_factors"] = factors
        mfa = state.get("mfaStatus") or state.get("authenticationState", {}).get("mfaStatus")
        if mfa:
            out["extra"]["mfa_status"] = mfa
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# LOOKUP 7: Microsoft (ResetPassword → oProofList)
# ─────────────────────────────────────────────

def lookup_microsoft(email: str) -> dict:
    out = {"registered": None, "rate_limited": False}
    s = cffi_requests.Session(impersonate="safari")
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        r = s.get(
            "https://account.live.com/ResetPassword.aspx",
            params={"mn": email.strip()},
            headers=headers,
            timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        if '"oProofList":[' not in r.text:
            out["registered"] = False
            return out
        import ast
        raw_str = "[" + r.text.split('"oProofList":[')[1].split("],")[0] + "]"
        proof_list = json.loads(raw_str)
        out["registered"] = True
        backup_email = None
        phones = []
        security_question = None
        two_fa = False
        for item in proof_list:
            t = item.get("type", "")
            name = item.get("name", "")
            if t == "Email" and "*" in name:
                backup_email = name
            elif t == "Sms":
                phones.append(name)
            elif t == "SQSA":
                security_question = name
            elif t == "TOTPAuthenticatorV2":
                two_fa = True
        if backup_email:
            out["backup_email"] = backup_email
        if phones:
            out["phones"] = phones
        if security_question:
            out["security_question"] = security_question
        if two_fa:
            out["two_fa"] = True
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# LOOKUP 8: Dropbox (via login error response)
# ─────────────────────────────────────────────

def lookup_dropbox(email: str) -> dict:
    out = {"registered": None, "rate_limited": False}
    s = cffi_requests.Session(impersonate=IMPERSONATE)
    headers = {
        "User-Agent": UA, "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.dropbox.com", "Referer": "https://www.dropbox.com/login",
    }
    try:
        # Get CSRF token from login page (Dropbox stores it in cookie 't' or '__Host-js_csrf')
        page = s.get("https://www.dropbox.com/login", headers={"User-Agent": UA}, timeout=TIMEOUT)
        token = (s.cookies.get("t") or s.cookies.get("__Host-js_csrf") or
                 re.search(r'name="t" value="([^"]+)"', page.text) and
                 re.search(r'name="t" value="([^"]+)"', page.text).group(1) or "")

        r = s.post(
            "https://www.dropbox.com/ajax_login",
            headers=headers,
            data={
                "login_email": email.strip(),
                "login_password": "Dropb0x_0SINT_99xX!",
                "t": token,
                "is_xhr": "true",
                "remember_me": "False",
                "cont": "https://www.dropbox.com/home",
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        if r.status_code == 200 and r.text.strip():
            raw_text = r.text
            if "funcaptcha" in raw_text.lower() or "captcha" in raw_text.lower():
                out["rate_limited"] = True
                out["note"] = "captcha_required"
                return out
            try:
                # Dropbox err is sometimes outside JSON: "err:{...}"
                json_start = raw_text.find("{")
                if json_start >= 0:
                    data = json.loads(raw_text[json_start:])
                else:
                    data = {}
                err = str(data.get("err", "")).lower()
                if "no account" in err or "not found" in err or "doesn't exist" in err:
                    out["registered"] = False
                elif "wrong password" in err or "incorrect" in err or data.get("has_2fa"):
                    out["registered"] = True
                elif "login_required" in raw_text:
                    out["registered"] = False
            except Exception:
                pass
        elif r.status_code == 401:
            pass
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# LOOKUP 9: Discord
# ─────────────────────────────────────────────

def lookup_discord(email: str) -> dict:
    out = {"registered": None, "rate_limited": False}
    headers = {
        "User-Agent": UA, "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://discord.com", "Referer": "https://discord.com/login",
        "X-Discord-Locale": "en-US",
    }
    try:
        r = cffi_requests.post(
            "https://discord.com/api/v9/auth/login",
            headers=headers,
            json={"login": email.strip(), "password": "Discord_0SINT_xX9!",
                  "undelete": False, "login_source": None, "gift_code_sku_id": None},
            impersonate=IMPERSONATE, timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        data = r.json() if r.status_code < 500 else {}
        if data.get("captcha_key") or "captcha_required" in str(data):
            out["rate_limited"] = True
            out["note"] = "captcha_required"
            return out
        if data.get("mfa") is True or data.get("token"):
            out["registered"] = True
            return out
        errors = data.get("errors", {})
        pw_errs = errors.get("password", {}).get("_errors", [])
        login_errs = errors.get("login", {}).get("_errors", [])
        login_codes = [e.get("code", "") for e in login_errs]
        if pw_errs:
            out["registered"] = True
        elif "INVALID_LOGIN" in login_codes or (login_errs and not pw_errs):
            out["registered"] = False
        elif r.status_code == 400 and not login_errs and not pw_errs:
            out["registered"] = True
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# LOOKUP 10: Steam
# ─────────────────────────────────────────────

def lookup_steam(email: str) -> dict:
    out = {"registered": None, "rate_limited": False}
    s = _session()
    headers = {
        "User-Agent": UA,
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Origin": "https://store.steampowered.com",
        "Referer": "https://store.steampowered.com/join/",
        "X-Requested-With": "XMLHttpRequest",
        "X-Prototype-Version": "1.7",
    }
    try:
        # Primary: signup checkavail — bAvailable=false means email in use
        r = s.post(
            "https://store.steampowered.com/join/checkavail/",
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            data={"accountname": email.strip(), "count": "1"},
            timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        if r.status_code == 200 and r.text.strip():
            try:
                data = r.json()
                avail = data.get("bAvailable")
                if avail is False:
                    out["registered"] = True
                    return out
                elif avail is True:
                    # Fallback: help wizard (confirms actual account registration)
                    pass
            except Exception:
                pass

        # Fallback: help wizard login info
        r2 = s.post(
            "https://help.steampowered.com/en/wizard/HelpWithLoginInfo",
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
            data={"email": email.strip(), "wizard_ajax": "1", "s": "4"},
            timeout=TIMEOUT,
        )
        text = r2.text.lower()
        for p in ("no accounts", "couldn't find", "not found", "no steam account", "unable to find"):
            if p in text:
                out["registered"] = False
                return out
        for p in ("account found", "accounts found", "we found", "select your account", "account associated"):
            if p in text:
                out["registered"] = True
                return out
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# LOOKUP 11: Skype — same Microsoft account system as lookup_microsoft
# ─────────────────────────────────────────────

def lookup_skype(email: str) -> dict:
    """Skype uses Microsoft accounts — same check as Microsoft recovery."""
    return lookup_microsoft(email)


# ─────────────────────────────────────────────
# LOOKUP 12: Twitch (password reset endpoint)
# ─────────────────────────────────────────────

def lookup_twitch(email: str) -> dict:
    out = {"registered": None, "rate_limited": False}
    headers = {
        "User-Agent": UA, "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
        "Origin": "https://www.twitch.tv", "Referer": "https://www.twitch.tv/",
    }
    try:
        r = cffi_requests.post(
            "https://passport.twitch.tv/password_reset_request",
            headers=headers,
            json={"email": email.strip()},
            impersonate=IMPERSONATE, timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        if r.status_code == 200:
            out["registered"] = True
            return out
        if r.status_code == 404:
            out["registered"] = False
            return out
        if r.text.strip():
            try:
                data = r.json()
                error = str(data.get("error", "")).lower()
                message = str(data.get("message", "")).lower()
                for ind in ("not found", "no user", "invalid", "unknown"):
                    if ind in error or ind in message:
                        out["registered"] = False
                        return out
            except Exception:
                pass
        if r.status_code == 400:
            out["registered"] = False
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# LOOKUP 13: Pinterest
# ─────────────────────────────────────────────

def lookup_pinterest(email: str) -> dict:
    out = {"registered": None, "rate_limited": False}
    s = cffi_requests.Session(impersonate=IMPERSONATE)
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "X-APP-VERSION": "58f07f9",
        "X-Pinterest-AppState": "active",
        "Origin": "https://www.pinterest.com",
        "Referer": "https://www.pinterest.com/",
    }
    try:
        page = s.get("https://www.pinterest.com/password/reset/", headers=headers, timeout=TIMEOUT)
        # Get CSRF from meta or response body
        csrf_m = re.search(r'"csrftoken"\s*:\s*"([^"]+)"', page.text)
        if csrf_m:
            csrf_val = csrf_m.group(1)
        else:
            # curl_cffi cookies accessed as dict
            csrf_val = s.cookies.get("csrftoken") or ""

        r = s.post(
            "https://www.pinterest.com/resource/UserPasswordResetEmailResource/create/",
            headers={**headers,
                     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                     "X-CSRFToken": csrf_val},
            data={
                "data": json.dumps({"options": {"email": email.strip()}, "context": {}}),
                "source_url": "/password/reset/",
                "_": "",
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        data = r.json() if r.status_code < 500 and r.text.strip() else {}
        rr = data.get("resource_response", {}) or {}
        status = rr.get("status", "")
        message = str(rr.get("message", "")).lower()
        code = rr.get("code", -99)

        if status == "success" or code == 0:
            out["registered"] = True
        elif "not found" in message or "no account" in message or code in (16, -1):
            out["registered"] = False
        elif r.status_code == 200 and not message:
            out["registered"] = True
        elif r.status_code in (400, 404):
            out["registered"] = False
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# LOOKUP 14: Tumblr
# ─────────────────────────────────────────────

def lookup_tumblr(email: str) -> dict:
    out = {"registered": None, "rate_limited": False}
    headers = {
        "User-Agent": UA, "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://www.tumblr.com", "Referer": "https://www.tumblr.com/login",
    }
    try:
        r = cffi_requests.post(
            "https://www.tumblr.com/api/v2/user/login",
            headers=headers,
            json={"email": email.strip(), "password": "Tumbl_0SINT_xX9!"},
            impersonate=IMPERSONATE, timeout=TIMEOUT,
        )
        if r.status_code == 429:
            out["rate_limited"] = True
            return out
        data = r.json() if r.status_code < 500 else {}
        meta = data.get("meta", {})
        status_code = meta.get("status")
        msg = str(meta.get("msg", "")).lower()
        if "password" in msg or "wrong" in msg or status_code in (403, 200):
            out["registered"] = True
        elif "not found" in msg or "no account" in msg or status_code == 404:
            out["registered"] = False
        elif r.status_code == 401:
            # Unauthorized with bad password = account exists
            out["registered"] = True
        elif r.status_code == 403:
            out["registered"] = True
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# ─────────────────────────────────────────────
# AGGREGATOR
# ─────────────────────────────────────────────

CHECKS = {
    "gravatar":   lookup_gravatar,
    "emailrep":   lookup_emailrep,
    "domain":     lookup_domain,
    "github":     lookup_github,
    "spotify":    lookup_spotify,
    "adobe":      lookup_adobe,
    "microsoft":  lookup_microsoft,
    "dropbox":    lookup_dropbox,
    "discord":    lookup_discord,
    "steam":      lookup_steam,
    "skype":      lookup_skype,
    "twitch":     lookup_twitch,
    "pinterest":  lookup_pinterest,
    "tumblr":     lookup_tumblr,
}


def run_all(email: str, workers: int = 8) -> dict:
    results: dict = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut_map = {pool.submit(fn, email): name for name, fn in CHECKS.items()}
        for fut in as_completed(fut_map):
            name = fut_map[fut]
            try:
                results[name] = fut.result()
            except Exception as exc:
                results[name] = {"error": str(exc)}
    return results


def build_report(email: str, raw: dict) -> dict:
    report: dict = {
        "email": email,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "profile": {},
        "domain_info": raw.get("domain", {}),
        "reputation": {},
        "registered_services": {},
        "summary": {},
    }

    # Profile from Gravatar
    grav = raw.get("gravatar", {})
    if grav.get("found"):
        for key in ("name", "avatar", "bio", "location", "profile_url",
                    "connected_accounts", "websites", "emails", "ims"):
            if key in grav:
                report["profile"][key] = grav[key]
        report["profile"]["gravatar_hash"] = grav.get("hash")

    # Profile extras from Skype
    skype = raw.get("skype", {})
    if skype.get("registered") and skype.get("display_name"):
        if "name" not in report["profile"]:
            report["profile"]["name"] = skype["display_name"]
        if "avatar" not in report["profile"] and skype.get("avatar"):
            report["profile"]["avatar"] = skype["avatar"]

    # Reputation from EmailRep
    erep = raw.get("emailrep", {})
    if erep.get("found"):
        for key in ("reputation", "suspicious", "blacklisted", "credentials_leaked",
                    "data_breach", "spam", "free_provider", "disposable", "deliverable",
                    "smtp_valid", "spoofable", "spf_strict", "dmarc_enforced",
                    "first_seen", "last_seen", "references", "profiles",
                    "domain_reputation", "domain_exists", "mx_records", "valid_mx"):
            if key in erep:
                report["reputation"][key] = erep[key]

    # Service registrations
    service_keys = {
        "github": "registered", "spotify": "registered", "adobe": "registered",
        "microsoft": "registered", "dropbox": "registered", "discord": "registered",
        "steam": "registered", "skype": "registered", "twitch": "registered",
        "pinterest": "registered", "tumblr": "registered",
    }
    for svc, key in service_keys.items():
        svc_data = raw.get(svc, {})
        entry: dict = {}
        reg = svc_data.get(key)
        if reg is True:
            entry["registered"] = True
        elif reg is False:
            entry["registered"] = False
        else:
            entry["registered"] = None
        if svc_data.get("rate_limited"):
            entry["rate_limited"] = True
        if svc_data.get("note"):
            entry["note"] = svc_data["note"]
        if svc_data.get("error"):
            entry["error"] = svc_data["error"]
        # Adobe extra
        if svc == "adobe" and svc_data.get("extra"):
            entry["details"] = svc_data["extra"]
        # Microsoft extra
        if svc == "microsoft":
            for k in ("has_password", "pref_credential", "throttle_status"):
                if k in svc_data:
                    entry[k] = svc_data[k]
        report["registered_services"][svc] = entry

    # Summary
    found_on = [s for s, d in report["registered_services"].items() if d.get("registered") is True]
    not_found_on = [s for s, d in report["registered_services"].items() if d.get("registered") is False]
    unknown = [s for s, d in report["registered_services"].items() if d.get("registered") is None]
    report["summary"] = {
        "registered_on": found_on,
        "not_registered_on": not_found_on,
        "unknown": unknown,
        "total_found": len(found_on),
        "has_profile_data": bool(report["profile"]),
        "has_reputation_data": bool(report["reputation"]),
        "is_suspicious": report["reputation"].get("suspicious", False),
        "credentials_leaked": report["reputation"].get("credentials_leaked", False),
        "data_breach": report["reputation"].get("data_breach", False),
    }

    return report


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def email_osint(email: str) -> dict:
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return {"error": "invalid_email", "email": email}
    raw = run_all(email)
    return build_report(email, raw)


def _print_human(report: dict):
    email = report.get("email", "")
    print(f"\n{'═'*60}")
    print(f"  EMAIL OSINT — {email}")
    print(f"  {report.get('generated', '')}")
    print(f"{'═'*60}")

    profile = report.get("profile", {})
    if profile:
        print("\n[PROFILE]")
        if profile.get("name"):
            print(f"  Name       : {profile['name']}")
        if profile.get("location"):
            print(f"  Location   : {profile['location']}")
        if profile.get("bio"):
            print(f"  Bio        : {profile['bio'][:120]}")
        if profile.get("avatar"):
            print(f"  Avatar     : {profile['avatar']}")
        if profile.get("profile_url"):
            print(f"  Gravatar   : {profile['profile_url']}")
        if profile.get("emails"):
            print(f"  Emails     : {', '.join(profile['emails'])}")
        if profile.get("websites"):
            for w in profile["websites"]:
                print(f"  Website    : {w.get('title', '')} → {w.get('url', '')}")
        if profile.get("connected_accounts"):
            print(f"  Linked accounts:")
            for a in profile["connected_accounts"]:
                print(f"    • {a.get('service', '?')}: {a.get('name', '')} {a.get('url', '')}")

    rep = report.get("reputation", {})
    if rep:
        print("\n[REPUTATION]")
        score = rep.get("reputation", "unknown")
        suspicious = "⚠  SUSPICIOUS" if rep.get("suspicious") else "clean"
        print(f"  Score      : {score}  ({suspicious})")
        if rep.get("credentials_leaked"):
            print(f"  ⚠  Credentials leaked in breaches")
        if rep.get("data_breach"):
            print(f"  ⚠  Found in data breaches")
        if rep.get("blacklisted"):
            print(f"  ⚠  Blacklisted")
        if rep.get("spam"):
            print(f"  ⚠  Spam flag")
        if rep.get("first_seen"):
            print(f"  First seen : {rep['first_seen']}")
        if rep.get("last_seen"):
            print(f"  Last seen  : {rep['last_seen']}")
        if rep.get("references") is not None:
            print(f"  References : {rep['references']}")
        if rep.get("profiles"):
            print(f"  Profiles   : {', '.join(rep['profiles'])}")
        flags = []
        for f in ("free_provider", "disposable", "deliverable", "smtp_valid"):
            if rep.get(f) is not None:
                flags.append(f"{f}={'yes' if rep[f] else 'no'}")
        if flags:
            print(f"  Flags      : {' | '.join(flags)}")

    domain_info = report.get("domain_info", {})
    if domain_info:
        print("\n[DOMAIN]")
        print(f"  Domain     : {domain_info.get('domain', '')}")
        if domain_info.get("mx_records"):
            print(f"  MX Records : {', '.join(domain_info['mx_records'][:3])}")
        if domain_info.get("a_records"):
            print(f"  A Records  : {', '.join(domain_info['a_records'][:3])}")

    svcs = report.get("registered_services", {})
    if svcs:
        print("\n[SERVICE REGISTRATIONS]")
        for svc, info in sorted(svcs.items()):
            reg = info.get("registered")
            rl = info.get("rate_limited", False)
            note = info.get("note", "")
            if reg is True:
                symbol = "✔"
                label = "REGISTERED"
            elif reg is False:
                symbol = "✘"
                label = "not found"
            elif rl:
                symbol = "⚡"
                label = "rate limited / captcha"
            else:
                symbol = "?"
                label = "unknown"
            extra = ""
            if svc == "adobe" and info.get("details"):
                d = info["details"]
                parts = []
                if d.get("masked_email"):
                    parts.append(f"email:{d['masked_email']}")
                if d.get("mfa_status"):
                    parts.append(f"mfa:{d['mfa_status']}")
                if d.get("mfa_factors"):
                    parts.append(f"factors:{','.join(d['mfa_factors'])}")
                extra = f" [{', '.join(parts)}]"
            if svc == "microsoft" and info.get("has_password") is not None:
                extra = f" [has_pwd={info['has_password']}]"
            if note:
                extra += f" ({note})"
            print(f"  {symbol} {svc:<14} {label}{extra}")

    summary = report.get("summary", {})
    print(f"\n{'─'*60}")
    print(f"  Found on {summary.get('total_found', 0)} services: {', '.join(summary.get('registered_on', [])) or 'none'}")
    if summary.get("is_suspicious"):
        print("  ⚠  Email flagged as SUSPICIOUS")
    if summary.get("credentials_leaked"):
        print("  ⚠  Credentials found in known leaks")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Email OSINT — all info, no API keys")
    ap.add_argument("email", help="Target email address")
    ap.add_argument("--json", action="store_true", help="Output raw JSON")
    ap.add_argument("--workers", type=int, default=8, help="Parallel workers (default 8)")
    args = ap.parse_args()

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", args.email):
        print(json.dumps({"error": "invalid_email"}, indent=2))
        sys.exit(1)

    report = email_osint(args.email)

    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    else:
        _print_human(report)
    sys.stdout.flush()
    os._exit(0)  # skip curl_cffi Win32 COM cleanup noise
