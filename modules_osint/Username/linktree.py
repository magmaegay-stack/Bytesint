import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def linktree_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@")

    result = {
        "target": clean,
        "service": "linktree",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        resp = requests.get(
            f"https://linktr.ee/{clean}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome120",
            timeout=12,
            allow_redirects=True,
        )

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            if ("this linktree doesn't exist" in html.lower()
                    or "we couldn't find" in html.lower()):
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

            return_data = {
                "username": clean,
                "profile_url": f"https://linktr.ee/{clean}",
                "status": "verified_active",
            }

            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"]
                title = re.sub(r'\s*\|.*$', '', title).strip()
                title = re.sub(r'\s*:.*$', '', title).strip()
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

            # extract links from __NEXT_DATA__
            nd_m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(\{.+?\})</script>', html, re.DOTALL)
            if nd_m:
                try:
                    nd = json.loads(nd_m.group(1))
                    account = (nd.get("props", {})
                                 .get("pageProps", {})
                                 .get("account", {}))
                    links = account.get("links", [])
                    if links:
                        return_data["link_count"] = len(links)
                        return_data["links"] = [
                            {"title": l.get("title", ""), "url": l.get("url", "")}
                            for l in links[:15] if l.get("url")
                        ]

                    if account.get("profileTitle") and not return_data.get("display_name"):
                        return_data["display_name"] = account["profileTitle"]
                    if account.get("description") and not return_data.get("bio"):
                        return_data["bio"] = account["description"][:200]
                    if account.get("profilePictureUrl") and not return_data.get("avatar_url"):
                        return_data["avatar_url"] = account["profilePictureUrl"]

                    # social integrations
                    integrations = account.get("socialLinks", [])
                    if integrations:
                        return_data["social_links"] = [
                            {"type": s.get("type"), "url": s.get("url")}
                            for s in integrations if s.get("url")
                        ]
                except Exception:
                    pass

            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v}

        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
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
    _res = linktree_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
