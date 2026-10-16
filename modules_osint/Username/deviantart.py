import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")


def deviantart_lookup(target: str) -> dict:
    clean = target.strip().lstrip("@").lower()

    result = {
        "target": clean,
        "service": "deviantart",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    try:
        # DeviantArt public user search API
        req = urllib.request.Request(
            f"https://www.deviantart.com/_napi/da-user-profile/api/init/about?username={clean}",
            headers={
                "User-Agent": ua,
                "Accept": "application/json",
                "Referer": f"https://www.deviantart.com/{clean}/about",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200:
                    data = json.loads(r.read().decode("utf-8", errors="replace"))
                    owner = data.get("owner", {})
                    if owner:
                        return_data = {
                            "username": owner.get("username", clean),
                            "profile_url": f"https://www.deviantart.com/{clean}",
                            "status": "verified_active",
                            "user_id": owner.get("userId"),
                            "is_watching": owner.get("isWatching", False),
                            "avatar_url": owner.get("userPicture") or None,
                        }
                        stats = owner.get("stats", {})
                        if stats:
                            return_data["watchers"] = stats.get("watchers", 0)
                            return_data["deviations"] = stats.get("userDeviations", 0)
                        about = data.get("grUser", {}).get("aboutMe") or None
                        if about:
                            return_data["about"] = re.sub(r'<[^>]+>', '', about)[:300]
                        result["result"] = "found"
                        result["return"] = {k: v for k, v in return_data.items() if v is not None and v != ""}
                        return result
        except urllib.error.HTTPError as e:
            if e.code == 404:
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

        # fallback: profile HTML page
        req2 = urllib.request.Request(
            f"https://www.deviantart.com/{clean}",
            headers={"User-Agent": ua, "Accept": "text/html"},
        )
        try:
            with urllib.request.urlopen(req2, timeout=15) as r2:
                if r2.status == 200:
                    html = r2.read().decode("utf-8", errors="replace")

                    if "Page Not Found" in html or "deactivated" in html.lower():
                        result["result"] = "not_found"
                        result["return"] = {"status": "not_exists"}
                        return result

                    return_data = {
                        "username": clean,
                        "profile_url": f"https://www.deviantart.com/{clean}",
                        "status": "verified_active",
                    }
                    og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    if og_title:
                        return_data["display_name"] = og_title.group(1).replace("on DeviantArt", "").strip().rstrip(" -–|")

                    og_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    if og_img and "deviantart" in og_img.group(1):
                        return_data["avatar_url"] = og_img.group(1)

                    watchers_m = re.search(r'"watchers_count"\s*:\s*(\d+)', html)
                    if watchers_m:
                        return_data["watchers"] = int(watchers_m.group(1))

                    result["result"] = "found"
                    result["return"] = {k: v for k, v in return_data.items() if v}
                    return result
        except urllib.error.HTTPError as e:
            if e.code == 404:
                result["result"] = "not_found"
                result["return"] = {"status": "not_exists"}
                return result

        result["result"] = "error"
        result["msg"] = "all_methods_failed"

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = deviantart_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
