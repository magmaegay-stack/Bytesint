import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def soundcloud_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "soundcloud",
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
        resp = requests.get(
            f"https://soundcloud.com/{clean}",
            headers=headers,
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        html = resp.text

        if "Sorry! We can't find that user." in html or "We can&#x27;t find that user" in html:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "username": clean,
            "profile_url": f"https://soundcloud.com/{clean}",
            "status": "verified_active",
        }

        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if og_title:
            title = og_title.group(1).strip()
            if "|" in title:
                title = title.split("|")[0].strip()
            return_data["display_name"] = title

        og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        if og_desc:
            return_data["description"] = og_desc.group(1)[:300]

        og_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og_img:
            img = og_img.group(1)
            return_data["avatar_url"] = img.replace("-t500x500", "-t500x500")

        # extract from JSON-LD
        jsonld_m = re.search(r'<script type="application/ld\+json"[^>]*>(\{.+?\})</script>', html, re.DOTALL)
        if jsonld_m:
            try:
                ld = json.loads(jsonld_m.group(1))
                if ld.get("name"):
                    return_data["display_name"] = ld["name"]
                if ld.get("interactionStatistic"):
                    for stat in (ld["interactionStatistic"] if isinstance(ld["interactionStatistic"], list) else [ld["interactionStatistic"]]):
                        itype = stat.get("interactionType", {})
                        if isinstance(itype, dict):
                            itype = itype.get("@type", "")
                        if "follow" in str(itype).lower():
                            return_data["followers"] = stat.get("userInteractionCount")
                        elif "listen" in str(itype).lower() or "play" in str(itype).lower():
                            return_data["plays"] = stat.get("userInteractionCount")
            except Exception:
                pass

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = soundcloud_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
