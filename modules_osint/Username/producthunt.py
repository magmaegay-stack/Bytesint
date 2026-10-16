import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def producthunt_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "producthunt",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        resp = requests.get(
            f"https://www.producthunt.com/@{clean}",
            impersonate="safari17_0",
            timeout=15,
            allow_redirects=True,
        )

        if resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            if "this page doesn't exist" in html.lower() or "404" in html[:300]:
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            return_data = {
                "username": clean,
                "profile_url": f"https://www.producthunt.com/@{clean}",
                "status": "verified_active",
            }

            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"]
                title = re.sub(r'\s*[-–|]\s*Product Hunt.*$', '', title, flags=re.IGNORECASE).strip()
                if title:
                    return_data["display_name"] = title

            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = og_desc["content"].strip()
                if desc and "product hunt" not in desc.lower():
                    return_data["bio"] = desc[:200]

            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                return_data["avatar_url"] = og_img["content"]

            # upvotes / products count
            upvotes_m = re.search(r'([\d,]+)\s+(?:upvote|point)', html, re.IGNORECASE)
            if upvotes_m:
                return_data["upvotes"] = upvotes_m.group(1).replace(",", "")

            products_m = re.search(r'([\d,]+)\s+(?:product|launch)', html, re.IGNORECASE)
            if products_m:
                return_data["products"] = products_m.group(1).replace(",", "")

            # headline / tagline
            tagline_el = soup.find("p", class_=re.compile(r"tagline|headline|subtitle"))
            if tagline_el:
                return_data["tagline"] = tagline_el.get_text(strip=True)[:150]

            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v}
        else:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = producthunt_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
