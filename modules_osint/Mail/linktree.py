import sys
import requests
from bs4 import BeautifulSoup
import json
from typing import Optional


def _fetch_linktree_user(username: str) -> Optional[dict]:
    url = f"https://linktr.ee/{username}"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    script_tag = soup.find("script", attrs={"id": "__NEXT_DATA__"})
    if not script_tag:
        return None

    try:
        data = json.loads(script_tag.contents[0])["props"]["pageProps"]
    except (KeyError, json.JSONDecodeError, IndexError):
        return None

    account = data.get("account")
    if not account:
        return None

    return {
        "username": account.get("username"),
        "ProfileUrl": f"https://linktr.ee/{account.get('username')}",
        "ProfilePicUrl": account.get("profilePictureUrl"),
        "id": account.get("id"),
        "tier": account.get("tier"),
        "isActive": account.get("isActive"),
        "description": account.get("description"),
        "createdAt": account.get("createdAt"),
        "updatedAt": account.get("updatedAt"),
    }


def check(username: str):
    try:
        user_info = _fetch_linktree_user(username)
        if user_info:
            return {"taken": True, "ExtraData": user_info}
        return {"taken": False, "ExtraData": {}}
    except Exception as e:
        return {"taken": False, "ExtraData": {"Error": str(e)}}


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = _fetch_linktree_user(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
