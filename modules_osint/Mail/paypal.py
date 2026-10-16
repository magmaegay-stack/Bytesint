import json
# language: Python 3.10+, file: paypal.py
# usage:  python paypal.py <email|phone|handle> [--debug] [--headful]
# install:
#   pip install playwright playwright-stealth phonenumbers rich requests
#   playwright install chromium

import argparse, asyncio, json, re, sys, time
from pathlib import Path
from urllib.parse import quote

import requests, phonenumbers
from rich.console import Console
from rich.table   import Table
from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

console = Console()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

RECOVER_PAGE  = "https://www.paypal.com/authflow/password-recovery/"
PAYPALME_PAGE = "https://www.paypal.com/paypalme/{h}"
VENMO_API     = "https://account.venmo.com/api/users?username={u}"
VENMO_PAGE    = "https://account.venmo.com/u/{u}"
WAYBACK_API   = "http://archive.org/wayback/available"

EMAIL_RE  = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE  = re.compile(r"^\+?\d[\d\s\-\(\)]{6,}$")
HANDLE_RE = re.compile(r"^(?:https?://)?(?:www\.)?paypal\.me/([A-Za-z0-9_.-]{3,20})/?$")

DEBUG = False


def classify(term):
    t = term.strip()
    if m := HANDLE_RE.match(t): return "handle", m.group(1)
    if EMAIL_RE.match(t):       return "email", t.lower()
    if PHONE_RE.match(t):
        try:
            n = phonenumbers.parse(t, None if t.startswith("+") else "US")
            if not phonenumbers.is_valid_number(n): raise ValueError
            return "phone", phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            sys.exit("invalid phone — include country code")
    sys.exit("input must be email, phone, or paypal.me handle")


def dbg(*a):
    if DEBUG: console.print(f"[dim][DEBUG] {' '.join(str(x) for x in a)}[/]")


# ───────────────────────────────  paypal recovery via headless browser  ───

async def paypal_recovery_playwright(kind: str, value: str, headful: bool) -> dict | None:
    """
    drive the real recovery flow in a stealth-patched chromium.
    captures the first XHR that returns a profile payload.
    """
    captured: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=not headful,
            args=["--disable-blink-features=AutomationControlled",
                  "--no-sandbox",
                  "--disable-features=IsolateOrigins,site-per-process"],
        )
        ctx = await browser.new_context(
            user_agent=UA,
            locale="en-US",
            timezone_id="Europe/Rome",
            viewport={"width": 1366, "height": 768},
        )
        page = await ctx.new_page()
        if stealth_async:
            await stealth_async(page)

        async def on_response(resp):
            u = resp.url
            if ("recovery" in u or "resolve" in u or "consumer" in u
                or "profile" in u or "lookup" in u) and resp.request.method == "POST":
                try:
                    j = await resp.json()
                    captured.append({"url": u, "status": resp.status, "json": j})
                    dbg("captured XHR", u, resp.status)
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            await page.goto(RECOVER_PAGE, wait_until="networkidle", timeout=45000)
        except Exception as e:
            dbg("goto err:", e)

        # wait up to 20s for captcha to self-solve or page to settle
        for _ in range(20):
            if "password-recovery" in page.url and "captcha" not in page.url:
                break
            await asyncio.sleep(1)

        # locate the input field — PayPal rotates ids, try a few
        selectors = ['input[name="email"]', 'input[id="email"]',
                     'input[type="email"]', 'input[name="identifier"]',
                     'input[placeholder*="mail" i]', 'input[placeholder*="phone" i]',
                     'input[autocomplete="username"]']
        box = None
        for sel in selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=4000)
                if el:
                    box = el; dbg("input found:", sel); break
            except Exception:
                continue

        if not box:
            dbg("no input found; saving screenshot debug_page.png")
            try: await page.screenshot(path="debug_page.png", full_page=True)
            except Exception: pass
            await browser.close()
            return None

        await box.fill(value)
        # submit button is usually [name=btnNext] / button[type=submit]
        for sel in ('button[name="btnNext"]', 'button[type="submit"]',
                    'button:has-text("Next")', 'button:has-text("Continue")'):
            try:
                b = await page.query_selector(sel)
                if b: await b.click(); dbg("submit clicked:", sel); break
            except Exception:
                pass

        # give XHR time to fire
        await asyncio.sleep(6)

        if DEBUG:
            try: await page.screenshot(path="debug_result.png", full_page=True)
            except Exception: pass

        # scrape visible profile hints too (name initials shown on screen)
        page_text = await page.content()
        await browser.close()

    # parse captured XHRs
    for cap in captured:
        j = cap["json"]
        hit = _extract_profile(j)
        if hit:
            hit["_endpoint"] = cap["url"]; hit["_http"] = cap["status"]
            return hit

    # fallback: regex the rendered DOM for name/initial/masked email
    dom_hit = {}
    if m := re.search(r'Hello,?\s+([A-Z][a-z]+)\s+([A-Z])\.', page_text):
        dom_hit["first_name"]   = m.group(1)
        dom_hit["last_initial"] = m.group(2)
    if m := re.search(r'([a-z0-9]{1,3}\*+@[a-z0-9.-]+\.[a-z]{2,})', page_text, re.I):
        dom_hit["masked_email"] = m.group(1)
    if m := re.search(r'(\+?\d{1,3}[\s\-]?\*+\d{2,4})', page_text):
        dom_hit["masked_phone"] = m.group(1)
    if dom_hit:
        dom_hit["_endpoint"] = "scraped from DOM"; return dom_hit
    return None


def _extract_profile(j):
    """deep-walk a json blob for anything useful."""
    found, stack = {}, [j]
    wanted = {
        "firstname":"first_name", "firstName":"first_name", "givenName":"first_name",
        "lastname":"last_name",   "lastName":"last_name",   "familyName":"last_name",
        "lastinitial":"last_initial","lastNameInitial":"last_initial",
        "fullname":"full_name",   "fullName":"full_name",   "displayName":"full_name",
        "maskedemail":"masked_email","emailMasked":"masked_email","hintEmail":"masked_email",
        "maskedphone":"masked_phone","phoneMasked":"masked_phone","hintPhone":"masked_phone",
        "photourl":"photo_url",   "photoUrl":"photo_url", "profilePhotoUrl":"photo_url",
        "country":"country",      "countryCode":"country",
        "payerid":"payer_id",     "payerId":"payer_id", "encryptedPayerId":"payer_id",
    }
    wl = {k.lower(): v for k, v in wanted.items()}
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                kl = k.lower()
                if kl in wl and v not in (None, "", [], {}):
                    found.setdefault(wl[kl], v)
                stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
    return found or None


# ───────────────────────────────  paypal.me  ──────────────────────────────

def paypalme_lookup(handle):
    r = requests.get(PAYPALME_PAGE.format(h=quote(handle)),
                     headers={"User-Agent": UA}, timeout=15, allow_redirects=True)
    dbg("paypal.me", r.status_code, len(r.content))
    if r.status_code != 200 or "sorry" in r.text.lower()[:4000]: return None
    name  = re.search(r'<meta property="og:title" content="([^"]+)"', r.text)
    photo = re.search(r'<meta property="og:image" content="([^"]+)"', r.text)
    about = re.search(r'<meta property="og:description" content="([^"]+)"', r.text)
    return {"handle": handle,
            "display_name": name.group(1)  if name  else None,
            "photo_url":    photo.group(1) if photo else None,
            "bio":          about.group(1) if about else None,
            "url":          r.url}


def wayback_first_seen(handle):
    try:
        r = requests.get(WAYBACK_API,
                         params={"url": f"paypal.me/{handle}", "timestamp": "20100101"},
                         timeout=10)
        snap = r.json().get("archived_snapshots", {}).get("closest")
        if snap and snap.get("available"):
            ts = snap["timestamp"]
            return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} (first wayback snapshot — lower bound)"
    except Exception:
        pass
    return None


# ───────────────────────────────  venmo bridge  ───────────────────────────

def venmo_lookup(username):
    """venmo (paypal-owned) exposes profile data unauthenticated. shared handles are common."""
    try:
        r = requests.get(VENMO_API.format(u=quote(username)),
                         headers={"User-Agent": UA,
                                  "Accept": "application/json"}, timeout=12)
        dbg("venmo api", r.status_code)
        if r.status_code == 200:
            j = r.json()
            data = (j.get("data") or [None])[0] if isinstance(j.get("data"), list) else j.get("data")
            if data:
                return {
                    "username":   data.get("username"),
                    "display":    data.get("display_name") or data.get("name"),
                    "first_name": data.get("first_name"),
                    "last_name":  data.get("last_name"),
                    "venmo_id":   data.get("id"),
                    "photo":      data.get("profile_picture_url") or (data.get("profile_picture") or {}).get("url"),
                    "created":    data.get("date_joined"),
                    "about":      data.get("about"),
                }
        # fallback: scrape the public page
        r = requests.get(VENMO_PAGE.format(u=quote(username)),
                         headers={"User-Agent": UA}, timeout=12)
        if r.status_code == 200 and "application/json" in r.text:
            m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>({.+?})</script>', r.text, re.DOTALL)
            if m:
                data = _extract_profile(json.loads(m.group(1)))
                if data: data["_source"] = "venmo_nextdata"; return data
    except Exception as e:
        dbg("venmo err", e)
    return None


# ───────────────────────────────  render  ─────────────────────────────────

def render(rec, pm, ve, age, term, kind):
    t = Table(title=f"PayPal/Venmo OSINT — {kind}: {term}",
              show_header=False, title_style="bold")
    t.add_column("field", style="cyan", no_wrap=True)
    t.add_column("value", style="white")
    def row(k, v):
        if v not in (None, "", [], False): t.add_row(k, str(v))

    if rec:
        t.add_row("── PayPal recovery ──", "")
        for k in ("first_name","last_name","last_initial","full_name",
                  "masked_email","masked_phone","photo_url","country","payer_id"):
            row(k.replace("_"," "), rec.get(k))
        row("endpoint", rec.get("_endpoint"))
    else:
        t.add_row("PayPal recovery", "[yellow]blocked by captcha / no account / rate-limited[/]")

    if pm:
        t.add_row("── paypal.me ──", "")
        row("display", pm["display_name"]); row("bio", pm["bio"])
        row("photo",   pm["photo_url"]);    row("url", pm["url"])

    if ve:
        t.add_row("── Venmo (PayPal-owned) ──", "")
        for k, v in ve.items(): row(k, v)

    row("account age (proxy)",  age)
    row("creation date (true)", "[dim]not exposed by any paypal endpoint[/]")
    console.print(t)


# ───────────────────────────────  main  ───────────────────────────────────

async def run(args):
    kind, value = classify(args.term)
    rec = pm = ve = age = None

    if kind in ("email", "phone"):
        rec = await paypal_recovery_playwright(kind, value, args.headful)
        guess = None
        if rec and rec.get("first_name"):
            tail = (rec.get("last_initial")
                    or (rec.get("last_name") or "")[:1])
            guess = (rec["first_name"] + tail).lower()
        if kind == "email":
            # venmo probe: try the email's local-part as username
            local = value.split("@")[0]
            ve = venmo_lookup(local)
        if guess:
            pm = paypalme_lookup(guess)
            if pm: age = wayback_first_seen(guess)
            if not ve: ve = venmo_lookup(guess)
    else:
        pm = paypalme_lookup(value)
        age = wayback_first_seen(value)
        ve = venmo_lookup(value)

    if args.json:
        print(json.dumps({"input": {"kind": kind, "value": value},
                          "paypal_recovery": rec, "paypalme": pm,
                          "venmo": ve, "age_proxy": age}, indent=2, default=str))
    else:
        render(rec, pm, ve, age, value, kind)


def main():
    global DEBUG
    ap = argparse.ArgumentParser()
    ap.add_argument("term")
    ap.add_argument("--json",    action="store_true")
    ap.add_argument("--debug",   action="store_true")
    ap.add_argument("--headful", action="store_true",
                    help="show the browser (useful when captcha wants a human click)")
    args = ap.parse_args()
    DEBUG = args.debug
    asyncio.run(run(args))


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = classify(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
