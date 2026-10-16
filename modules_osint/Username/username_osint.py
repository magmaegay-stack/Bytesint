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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

from github import github_lookup
from gitlab import gitlab_lookup
from reddit import reddit_lookup
from hackernews import hackernews_lookup
from keybase import keybase_lookup
from twitch import twitch_lookup
from youtube import youtube_lookup
from instagram import instagram_lookup
from snapchat import snapchat_lookup
from tiktok import tiktok_lookup
from twitter import twitter_lookup
from facebook import facebook_lookup
from tumblr import tumblr_lookup
from pinterest import pinterest_lookup
from soundcloud import soundcloud_lookup
from spotify import spotify_lookup
from steam import steam_lookup
from roblox import roblox_lookup
from minecraft import minecraft_lookup
from chess import chess_lookup
from duolingo import duolingo_lookup
from npm import npm_lookup
from medium import medium_lookup
from patreon import patreon_lookup
from deviantart import deviantart_lookup
from stackoverflow import stackoverflow_lookup
from vimeo import vimeo_lookup
from pypi import pypi_lookup
from dockerhub import dockerhub_lookup
from linkedin import linkedin_lookup


# ──────────────────────────────────────────────────────────────────────────────
# Additional lookups not in existing modules
# ──────────────────────────────────────────────────────────────────────────────

def lookup_telegram(username: str) -> dict:
    """Check Telegram via t.me/{username}."""
    clean = username.strip().lstrip("@")
    out = {"service": "telegram", "target": clean, "result": "not_found", "return": {}}
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://t.me/{clean}",
            headers={"Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"},
            timeout=12,
            allow_redirects=True,
        )
        if r.status_code == 200:
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            # Generic template page shown for non-existent usernames
            not_found_phrases = [
                "if you have telegram, you can contact",
                "channel doesn't seem to exist",
                "bot doesn't seem to exist",
                "user doesn't seem to exist",
                "sorry, but you can't",
            ]
            if any(p in html.lower() for p in not_found_phrases):
                out["result"] = "not_found"
                return out

            # Real profiles have a tgme_page_title div with actual content
            title_el = soup.find("div", class_="tgme_page_title")
            if not title_el or not title_el.get_text(strip=True):
                out["result"] = "not_found"
                return out

            return_data = {
                "username": clean,
                "profile_url": f"https://t.me/{clean}",
                "status": "verified_active",
                "display_name": title_el.get_text(strip=True),
            }

            desc_el = soup.find("div", class_="tgme_page_description")
            if desc_el:
                return_data["description"] = desc_el.get_text(strip=True)[:300]

            extra_el = soup.find("div", class_="tgme_page_extra")
            if extra_el:
                count_m = re.search(r'([\d\s,]+)\s*(subscriber|member|follower)', extra_el.get_text(), re.IGNORECASE)
                if count_m:
                    return_data["subscribers"] = count_m.group(1).strip().replace(" ", "")

            img_el = soup.find("img", class_="tgme_page_photo_image")
            if img_el and img_el.get("src"):
                return_data["avatar_url"] = img_el["src"]

            out["result"] = "found"
            out["return"] = {k: v for k, v in return_data.items() if v}
        elif r.status_code == 404:
            out["result"] = "not_found"
    except Exception as e:
        out["result"] = "error"
        out["msg"] = str(e)
    return out


def lookup_mastodon(username: str) -> dict:
    """Check Mastodon.social via API."""
    clean = username.strip().lstrip("@")
    out = {"service": "mastodon", "target": clean,
           "result": "not_found", "return": {}}
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://mastodon.social/api/v1/accounts/lookup?acct={clean}",
            headers={"Accept": "application/json"},
            timeout=12,
        )
        if r.status_code == 200:
            d = r.json()
            if d.get("id"):
                return_data = {
                    "username": d.get("username", clean),
                    "display_name": d.get("display_name") or None,
                    "profile_url": d.get("url"),
                    "status": "verified_active",
                    "id": d.get("id"),
                    "followers": d.get("followers_count", 0),
                    "following": d.get("following_count", 0),
                    "posts": d.get("statuses_count", 0),
                    "avatar_url": d.get("avatar"),
                    "bio": BeautifulSoup(d.get("note", ""), "html.parser").get_text(strip=True)[:200] or None,
                    "is_bot": d.get("bot", False),
                    "locked": d.get("locked", False),
                }
                if d.get("created_at"):
                    return_data["created"] = d["created_at"][:10]
                out["result"] = "found"
                out["return"] = {k: v for k, v in return_data.items() if v is not None and v != ""}
        elif r.status_code == 404:
            out["result"] = "not_found"
        elif r.status_code == 429:
            out["result"] = "error"
            out["msg"] = "rate_limited"
    except Exception as e:
        out["result"] = "error"
        out["msg"] = str(e)
    return out


def lookup_linktree(username: str) -> dict:
    """Check Linktree profile."""
    clean = username.strip().lstrip("@")
    out = {"service": "linktree", "target": clean,
           "result": "not_found", "return": {}}
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://linktr.ee/{clean}",
            headers={"Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"},
            timeout=12,
            allow_redirects=True,
        )
        if r.status_code == 200:
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            not_found = (
                "This Linktree doesn't exist" in html
                or "We couldn't find" in html
                or "404" in html[:500]
            )
            if not_found:
                out["result"] = "not_found"
                return out

            return_data = {
                "username": clean,
                "profile_url": f"https://linktr.ee/{clean}",
                "status": "verified_active",
            }

            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
                # strip " | Linktree" suffix and everything after ":"
                title = re.sub(r'\s*\|.*$', '', title)
                title = re.sub(r'\s*:.*$', '', title)
                if title and title.lower() != "linktree":
                    return_data["display_name"] = title

            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = og_desc["content"].strip()
                if desc and "linktree" not in desc.lower():
                    return_data["bio"] = desc[:200]

            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                img = og_img["content"]
                if "default" not in img.lower():
                    return_data["avatar_url"] = img

            # count links
            next_data_m = re.search(r'"__NEXT_DATA__"[^>]*>(\{.*?\})</script>', html, re.DOTALL)
            if next_data_m:
                try:
                    nd = json.loads(next_data_m.group(1))
                    links = (nd.get("props", {})
                               .get("pageProps", {})
                               .get("account", {})
                               .get("links", []))
                    if links:
                        return_data["link_count"] = len(links)
                        return_data["links"] = [
                            {"title": l.get("title", ""), "url": l.get("url", "")}
                            for l in links[:10] if l.get("url")
                        ]
                except Exception:
                    pass

            out["result"] = "found"
            out["return"] = {k: v for k, v in return_data.items() if v}
        elif r.status_code == 404:
            out["result"] = "not_found"
    except Exception as e:
        out["result"] = "error"
        out["msg"] = str(e)
    return out


def lookup_producthunt(username: str) -> dict:
    """Check Product Hunt profile."""
    clean = username.strip().lstrip("@")
    out = {"service": "producthunt", "target": clean,
           "result": "not_found", "return": {}}
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://www.producthunt.com/@{clean}",
            headers={"Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"},
            timeout=12,
            allow_redirects=True,
        )
        if r.status_code == 200:
            html = r.text
            if "This page doesn't exist" in html or "404" in html[:200]:
                out["result"] = "not_found"
                return out
            soup = BeautifulSoup(html, "html.parser")
            return_data = {
                "username": clean,
                "profile_url": f"https://www.producthunt.com/@{clean}",
                "status": "verified_active",
            }
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].replace("Product Hunt", "").strip(" –-")
                if title:
                    return_data["display_name"] = title
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                return_data["bio"] = og_desc["content"][:200]
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                return_data["avatar_url"] = og_img["content"]
            out["result"] = "found"
            out["return"] = {k: v for k, v in return_data.items() if v}
        elif r.status_code == 404:
            out["result"] = "not_found"
    except Exception as e:
        out["result"] = "error"
        out["msg"] = str(e)
    return out


def lookup_gravatar(username: str) -> dict:
    """Check Gravatar by username (treats as email handle)."""
    import hashlib
    clean = username.strip().lstrip("@").lower()
    out = {"service": "gravatar", "target": clean,
           "result": "not_found", "return": {}}
    try:
        # Gravatar looks up by MD5 of email — we hash username@gmail.com as probe
        email_guess = f"{clean}@gmail.com"
        md5 = hashlib.md5(email_guess.encode()).hexdigest()
        s = cffi_requests.Session(impersonate="chrome120")
        r = s.get(
            f"https://www.gravatar.com/{md5}.json",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if r.status_code == 200:
            d = r.json()
            entry = d.get("entry", [{}])[0]
            if entry.get("id"):
                return_data = {
                    "username": entry.get("preferredUsername", clean),
                    "profile_url": entry.get("profileUrl"),
                    "status": "verified_active",
                    "display_name": entry.get("displayName"),
                    "avatar_url": entry.get("thumbnailUrl"),
                }
                if entry.get("aboutMe"):
                    return_data["bio"] = entry["aboutMe"][:200]
                if entry.get("currentLocation"):
                    return_data["location"] = entry["currentLocation"]
                if entry.get("accounts"):
                    return_data["linked_accounts"] = [
                        {"service": a.get("shortname"), "url": a.get("url")}
                        for a in entry["accounts"][:10] if a.get("shortname")
                    ]
                out["result"] = "found"
                out["return"] = {k: v for k, v in return_data.items() if v}
        elif r.status_code == 404:
            out["result"] = "not_found"
    except Exception as e:
        out["result"] = "error"
        out["msg"] = str(e)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Category mapping for output grouping
# ──────────────────────────────────────────────────────────────────────────────

CATEGORIES = {
    "social": ["twitter", "instagram", "facebook", "snapchat", "tiktok",
               "telegram", "mastodon", "linktree"],
    "video": ["youtube", "twitch", "vimeo", "tiktok"],
    "development": ["github", "gitlab", "stackoverflow", "npm", "pypi", "dockerhub",
                    "hackernews", "keybase"],
    "gaming": ["steam", "roblox", "minecraft", "chess"],
    "creative": ["deviantart", "soundcloud", "spotify", "tumblr", "pinterest",
                 "medium", "patreon", "behance", "dribbble"],
    "professional": ["linkedin", "producthunt"],
    "other": ["reddit", "duolingo", "gravatar"],
}


# ──────────────────────────────────────────────────────────────────────────────
# Main aggregator
# ──────────────────────────────────────────────────────────────────────────────

def username_osint(username: str) -> dict:
    clean = username.strip().lstrip("@")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    tasks = {
        # social
        "twitter":       lambda: twitter_lookup(clean),
        "instagram":     lambda: instagram_lookup(clean),
        "facebook":      lambda: facebook_lookup(clean),
        "snapchat":      lambda: snapchat_lookup(clean),
        "tiktok":        lambda: tiktok_lookup(clean),
        "telegram":      lambda: lookup_telegram(clean),
        "mastodon":      lambda: lookup_mastodon(clean),
        "linktree":      lambda: lookup_linktree(clean),
        # video
        "youtube":       lambda: youtube_lookup(clean),
        "twitch":        lambda: twitch_lookup(clean),
        "vimeo":         lambda: vimeo_lookup(clean),
        # development
        "github":        lambda: github_lookup(clean),
        "gitlab":        lambda: gitlab_lookup(clean),
        "stackoverflow": lambda: stackoverflow_lookup(clean),
        "npm":           lambda: npm_lookup(clean),
        "pypi":          lambda: pypi_lookup(clean),
        "dockerhub":     lambda: dockerhub_lookup(clean),
        "hackernews":    lambda: hackernews_lookup(clean),
        "keybase":       lambda: keybase_lookup(clean),
        # gaming
        "steam":         lambda: steam_lookup(clean),
        "roblox":        lambda: roblox_lookup(clean),
        "minecraft":     lambda: minecraft_lookup(clean),
        "chess":         lambda: chess_lookup(clean),
        # creative
        "soundcloud":    lambda: soundcloud_lookup(clean),
        "spotify":       lambda: spotify_lookup(clean),
        "tumblr":        lambda: tumblr_lookup(clean),
        "pinterest":     lambda: pinterest_lookup(clean),
        "deviantart":    lambda: deviantart_lookup(clean),
        "medium":        lambda: medium_lookup(clean),
        "patreon":       lambda: patreon_lookup(clean),
        # professional
        "linkedin":      lambda: linkedin_lookup(clean),
        "producthunt":   lambda: lookup_producthunt(clean),
        # other
        "reddit":        lambda: reddit_lookup(clean),
        "duolingo":      lambda: duolingo_lookup(clean),
        "gravatar":      lambda: lookup_gravatar(clean),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(fn): name for name, fn in tasks.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                results[name] = fut.result()
            except Exception as e:
                results[name] = {
                    "target": clean, "service": name,
                    "result": "error", "msg": str(e), "return": {},
                }

    # ── classify results ──────────────────────────────────────────────────────
    found = {}
    not_found = []
    errors = []

    for name, r in results.items():
        status = r.get("result", "")
        if status == "found":
            ret = r.get("return", {})
            found[name] = {
                "profile_url": ret.get("profile_url") or ret.get("canonical_url"),
                "display_name": (ret.get("display_name") or ret.get("full_name")
                                 or ret.get("channel_name") or ret.get("nickname")
                                 or ret.get("name")),
                "bio": (ret.get("bio") or ret.get("biography") or ret.get("signature")
                        or ret.get("description")),
                "followers": (ret.get("followers") or ret.get("followers_text")
                              or ret.get("subscribers")),
                "avatar_url": ret.get("avatar_url"),
                "extra": {},
            }
            # service-specific extras
            for k in ("location", "email", "website", "twitter", "company",
                      "public_repos", "total_karma", "is_verified", "created",
                      "joined", "videos", "link_count", "links", "linked_accounts"):
                val = ret.get(k)
                if val is not None and val not in ("", False, 0):
                    found[name]["extra"][k] = val
            # strip None/empty from top-level
            found[name] = {k: v for k, v in found[name].items() if v}
        elif status in ("not_found",):
            not_found.append(name)
        elif status in ("error",):
            errors.append({"service": name, "msg": r.get("msg", "")})

    # ── group found by category ────────────────────────────────────────────────
    found_by_category = {}
    for svc in found:
        placed = False
        for cat, services in CATEGORIES.items():
            if svc in services:
                found_by_category.setdefault(cat, {})[svc] = found[svc]
                placed = True
                break
        if not placed:
            found_by_category.setdefault("other", {})[svc] = found[svc]

    # ── collect all display names to detect cross-platform identity ───────────
    names = {}
    locations = {}
    for svc, info in found.items():
        dn = info.get("display_name")
        if dn:
            names[svc] = dn
        loc = (info.get("extra") or {}).get("location")
        if loc:
            locations[svc] = loc

    output = {
        "username": clean,
        "generated": generated,
        "profiles": found_by_category,
        "summary": {
            "total_lookups": len(tasks),
            "found_count": len(found),
            "not_found_count": len(not_found),
            "error_count": len(errors),
            "found_on": sorted(found.keys()),
            "display_names": names,
            "locations": locations,
        },
        "errors": errors,
        "raw": results,
    }

    return output


# ──────────────────────────────────────────────────────────────────────────────
# Human-readable output
# ──────────────────────────────────────────────────────────────────────────────

def print_human(data: dict) -> None:
    username = data.get("username", "?")
    gen = data.get("generated", "")
    summary = data.get("summary", {})
    profiles = data.get("profiles", {})
    errors = data.get("errors", [])

    print(f"\n{'='*64}")
    print(f"  USERNAME OSINT — @{username}")
    print(f"  {gen}")
    print(f"{'='*64}")
    print(f"  Found: {summary.get('found_count',0)}/{summary.get('total_lookups',0)} platforms")

    if profiles:
        for category, services in profiles.items():
            if not services:
                continue
            print(f"\n[{category.upper()}]")
            for svc, info in services.items():
                url = info.get("profile_url", "")
                display = info.get("display_name", "")
                bio = info.get("bio", "")
                followers = info.get("followers", "")

                line = f"  {svc:<16}"
                if display:
                    line += f" {display}"
                if followers:
                    line += f"  ({followers} followers)"
                print(line)

                if url:
                    print(f"    url      : {url}")
                if bio:
                    print(f"    bio      : {bio[:100]}")
                extra = info.get("extra", {})
                if extra:
                    for k, v in list(extra.items())[:4]:
                        if isinstance(v, list):
                            v = f"[{len(v)} items]"
                        print(f"    {k:<10}: {str(v)[:80]}")

    if summary.get("display_names"):
        print(f"\n[IDENTITY CROSS-REFERENCE]")
        for svc, name in summary["display_names"].items():
            print(f"  {svc:<16}: {name}")

    if summary.get("locations"):
        print(f"\n[LOCATIONS]")
        for svc, loc in summary["locations"].items():
            print(f"  {svc:<16}: {loc}")

    if errors:
        print(f"\n[ERRORS] ({len(errors)})")
        for e in errors[:5]:
            print(f"  {e.get('service','?'):<16}: {e.get('msg','')[:80]}")

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Username OSINT master module")
    parser.add_argument("username", help="Username to look up (e.g. john_doe)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    result = username_osint(args.username)

    if args.json:
        sys.stdout.write(json.dumps(result, indent=4, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        os._exit(0)
    else:
        print_human(result)
        sys.stdout.flush()
        os._exit(0)
