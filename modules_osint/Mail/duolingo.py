import sys
import json
import io
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == 'nt':
    os.system('chcp 65001 >nul')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SERVICE_NAME = "duolingo"
_LOOKUP_URL = "https://android-api-cf.duolingo.com/2017-06-30/users"
_LOOKUP_FIELDS = (
    "users{id,username,name,bio,picture,totalXp,streak,streakData,"
    "creationDate,hasPlus,hasRecentActivity15,learningLanguage,"
    "fromLanguage,location,roles,courses{id,title,learningLanguage,"
    "fromLanguage,xp},subscriberLevel}"
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.duolingo.com/",
}

def _format_date(ts) -> str | None:
    if not ts:
        return None
    try:
        t = int(ts)
        if t > 1e10:
            t //= 1000
        return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return str(ts)

def _normalize_avatar(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    elif not url.startswith("https://"):
        url = "https://" + url.lstrip("/")
    if ("ssr-avatars" in url or "/avatars/" in url) and not re.search(
        r"/(xxlarge|xlarge|large|medium|small)$", url
    ):
        url = url.rstrip("/") + "/xxlarge"
    return url

def duolingo_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    
    result = {
        "target": clean_target,
        "service": SERVICE_NAME,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    try:
        response = requests.get(
            _LOOKUP_URL, 
            headers=_HEADERS,
            params={"username": clean_target, "fields": _LOOKUP_FIELDS},
            impersonate="chrome120",
            timeout=12,
        )
        
        if response.status_code != 200:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        data_json = response.json() or {}
        users = data_json.get("users") or []
        if not users:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        data = users[0]
        
        courses = []
        for course in data.get("courses", []) or []:
            courses.append({
                "id": course.get("id"),
                "title": course.get("title"),
                "learning": course.get("learningLanguage"),
                "from": course.get("fromLanguage"),
                "xp": course.get("xp"),
            })

        longest_streak = None
        streak_data = data.get("streakData") or {}
        prev_streak = streak_data.get("previousStreak") or {}
        if isinstance(prev_streak, dict) and prev_streak.get("length"):
            longest_streak = prev_streak.get("length")

        username = data.get("username")
        profile_url = f"https://www.duolingo.com/profile/{username}" if username else None

        return_data = {
            "id": str(data.get("id")) if data.get("id") else None,
            "name": data.get("name"),
            "username": username,
            "created_at": _format_date(data.get("creationDate")),
            "total_xp": data.get("totalXp"),
            "streak": data.get("streak"),
            "longest_streak": longest_streak,
            "subscriber_level": data.get("subscriberLevel"),
            "is_plus": data.get("hasPlus"),
            "recent_activity": data.get("hasRecentActivity15"),
            "current_learning": data.get("learningLanguage"),
            "native_language": data.get("fromLanguage"),
            "location": data.get("location"),
            "avatar_url": _normalize_avatar(data.get("picture")),
            "profile_url": profile_url,
            "roles": data.get("roles") or [],
            "courses_progress": courses,
            "status": "verified_active"
        }

        # Pulisce i campi vuoti o nulli
        cleaned_return = {k: v for k, v in return_data.items() if v is not None and v != "" and v != []}

        result["result"] = "found"
        result["return"] = cleaned_return

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = _format_date(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
