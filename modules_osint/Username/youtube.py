import sys
import json
import io
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == 'nt':
    os.system('chcp 65001 >nul')

# Cookie SOCS bypassa la consent page di Google per IP europei
BYPASS_COOKIES = {
    "SOCS": "CAESEwgDEgk0OTA5NjQ3NjIaAmVuIAEaBgiAsL2nBg",
    "CONSENT": "YES+cb",
}

def youtube_lookup(target: str) -> dict:
    clean = target.strip().lstrip('@')

    result = {
        "target": clean,
        "service": "youtube",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    urls_to_try = [
        f"https://www.youtube.com/@{clean}",
        f"https://www.youtube.com/c/{clean}",
        f"https://www.youtube.com/user/{clean}",
    ]

    resp = None
    final_url = ""
    for url in urls_to_try:
        try:
            r = requests.get(
                url, headers=headers, cookies=BYPASS_COOKIES,
                impersonate="chrome120", timeout=15, allow_redirects=True
            )
            # Evita la consent page
            if "consent.youtube.com" in r.url or "consent.google.com" in r.url:
                continue
            if r.status_code == 200:
                resp = r
                final_url = r.url
                break
        except Exception:
            continue

    if not resp:
        result["result"] = "not_found"
        result["return"] = {"status": "not_exists"}
        return result

    text = resp.text

    # Verifica 404
    if "yt-page-type-not-found" in text or '"pageId":"error-page"' in text:
        result["result"] = "not_found"
        result["return"] = {"status": "not_exists"}
        return result

    soup = BeautifulSoup(text, "html.parser")
    return_data = {"profile_url": final_url, "status": "verified_active"}

    # Nome canale
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        name = og_title["content"].strip()
        if name and name.lower() not in ("youtube", ""):
            return_data["channel_name"] = name

    # Descrizione
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        desc = og_desc["content"].strip()
        if desc:
            return_data["description"] = desc

    # Avatar
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        return_data["avatar_url"] = og_img["content"].strip()

    # URL canonico (@handle)
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        return_data["canonical_url"] = canonical["href"]

    # Estrazione dal JSON ytInitialData
    script_text = ""
    for script in soup.find_all("script"):
        if script.string and "ytInitialData" in script.string:
            script_text = script.string
            break

    if script_text:
        m = re.search(r'"subscriberCountText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"', script_text)
        if not m:
            m = re.search(r'"subscriberCountText"\s*:\s*"([^"]+)"', script_text)
        if m:
            return_data["subscribers"] = m.group(1)

        m = re.search(r'"videosCountText"\s*:\s*\{\s*"runs"\s*:\s*\[\{"text"\s*:\s*"([^"]+)"', script_text)
        if m:
            return_data["videos_count"] = m.group(1)

        m = re.search(r'"channelId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"', script_text)
        if m:
            return_data["channel_id"] = m.group(1)

        m = re.search(r'"country"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"', script_text)
        if m:
            return_data["country"] = m.group(1)

        m = re.search(r'"joinedDateText".*?"text"\s*:\s*"([^"]+)"', script_text)
        if m:
            return_data["joined"] = m.group(1)

        m = re.search(r'"viewCountText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"', script_text)
        if m:
            return_data["total_views"] = m.group(1)

    if not return_data.get("channel_name"):
        result["result"] = "not_found"
        result["return"] = {"status": "not_exists"}
        return result

    result["result"] = "found"
    result["return"] = return_data
    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = youtube_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
