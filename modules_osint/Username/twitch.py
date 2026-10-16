import sys
import json
import io
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == 'nt':
    os.system('chcp 65001 >nul')

TWITCH_GQL = "https://gql.twitch.tv/gql"
CLIENT_ID  = "kimne78kx3ncx6brgo4mv6wki5h1ko"

def twitch_lookup(target: str) -> dict:
    clean = target.strip().lstrip('@').lower()

    result = {
        "target": clean,
        "service": "twitch",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "Client-Id": CLIENT_ID,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    payload = [
        {
            "operationName": "SearchResultsPage_SearchResults",
            "variables": {
                "query": clean,
                "options": {
                    "targets": [{"index": "USER"}]
                }
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "ee977ac21b324669b4d109eda9e7f6f3e441d9de72d78f1b7b0c0c6e75c4bb00"
                }
            }
        }
    ]

    # Approccio più diretto: query senza hash persistito
    query_payload = [
        {
            "query": """
            query {
              user(login: "%s") {
                id
                login
                displayName
                description
                createdAt
                profileImageURL(width: 300)
                primaryColorHex
                roles {
                  isPartner
                  isAffiliate
                  isStaff
                }
                stream {
                  id
                  title
                  viewersCount
                  type
                  game {
                    name
                  }
                }
                lastBroadcast {
                  startedAt
                  title
                }
                followers {
                  totalCount
                }
              }
            }
            """ % clean
        }
    ]

    try:
        resp = requests.post(
            TWITCH_GQL,
            headers=headers,
            json=query_payload,
            impersonate="chrome120",
            timeout=15,
        )

        if resp.status_code != 200:
            result["result"] = "error"
            result["msg"] = f"HTTP {resp.status_code}"
            return result

        data = resp.json()
        user_data = None
        if isinstance(data, list) and data:
            user_data = data[0].get("data", {}).get("user")

        if not user_data:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        return_data = {
            "id": user_data.get("id"),
            "login": user_data.get("login"),
            "display_name": user_data.get("displayName"),
            "profile_url": f"https://www.twitch.tv/{clean}",
            "status": "verified_active",
        }

        if user_data.get("description"):
            return_data["bio"] = user_data["description"]
        if user_data.get("profileImageURL"):
            return_data["avatar_url"] = user_data["profileImageURL"]
        if user_data.get("primaryColorHex"):
            return_data["color"] = "#" + user_data["primaryColorHex"]
        if user_data.get("createdAt"):
            return_data["created_at"] = user_data["createdAt"][:10]

        roles = user_data.get("roles") or {}
        if roles.get("isPartner"):
            return_data["is_partner"] = True
        if roles.get("isAffiliate"):
            return_data["is_affiliate"] = True
        if roles.get("isStaff"):
            return_data["is_staff"] = True

        followers = user_data.get("followers") or {}
        if followers.get("totalCount") is not None:
            return_data["followers"] = followers["totalCount"]

        stream = user_data.get("stream")
        if stream:
            return_data["is_live"] = True
            return_data["live_title"] = stream.get("title")
            return_data["viewers"] = stream.get("viewersCount")
            game = stream.get("game") or {}
            if game.get("name"):
                return_data["live_game"] = game["name"]
        else:
            return_data["is_live"] = False

        last_bcast = user_data.get("lastBroadcast") or {}
        if last_bcast.get("startedAt"):
            return_data["last_broadcast"] = last_bcast["startedAt"][:10]

        result["result"] = "found"
        result["return"] = return_data

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = twitch_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
