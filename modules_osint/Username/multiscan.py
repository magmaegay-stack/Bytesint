import json
import os
import sys
import concurrent.futures
import importlib.util
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODULES = [
    ("github",       "github_lookup"),
    ("gitlab",       "gitlab_lookup"),
    ("reddit",       "reddit_lookup"),
    ("hackernews",   "hackernews_lookup"),
    ("keybase",      "keybase_lookup"),
    ("twitch",       "twitch_lookup"),
    ("youtube",      "youtube_lookup"),
    ("instagram",    "instagram_lookup"),
    ("snapchat",     "snapchat_lookup"),
    ("tiktok",       "tiktok_lookup"),
    ("twitter",      "twitter_lookup"),
    ("facebook",     "facebook_lookup"),
    ("tumblr",       "tumblr_lookup"),
    ("pinterest",    "pinterest_lookup"),
    ("soundcloud",   "soundcloud_lookup"),
    ("spotify",      "spotify_lookup"),
    ("steam",        "steam_lookup"),
    ("roblox",       "roblox_lookup"),
    ("minecraft",    "minecraft_lookup"),
    ("chess",        "chess_lookup"),
    ("duolingo",     "duolingo_lookup"),
    ("npm",          "npm_lookup"),
    ("medium",       "medium_lookup"),
    ("patreon",      "patreon_lookup"),
    ("deviantart",   "deviantart_lookup"),
    ("stackoverflow","stackoverflow_lookup"),
    ("linkedin",     "linkedin_lookup"),
]


def _run_module(name: str, func_name: str, username: str) -> dict:
    try:
        path = os.path.join(BASE_DIR, f"{name}.py")
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        func = getattr(mod, func_name)
        return func(username)
    except Exception as e:
        return {
            "target": username,
            "service": name,
            "result": "error",
            "msg": str(e),
            "return": {},
        }


def multiscan(username: str) -> dict:
    result = {
        "target": username,
        "service": "username_multiscan",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "modules_run": len(MODULES),
        "found": [],
        "not_found": [],
        "errors": [],
        "results": {},
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = {
            ex.submit(_run_module, name, func, username): name
            for name, func in MODULES
        }
        for fut in concurrent.futures.as_completed(futures):
            name = futures[fut]
            try:
                res = fut.result()
                result["results"][name] = res
                state = res.get("result", "error")
                if state == "found":
                    result["found"].append(name)
                elif state == "not_found":
                    result["not_found"].append(name)
                else:
                    result["errors"].append(name)
            except Exception as e:
                result["errors"].append(name)
                result["results"][name] = {"result": "error", "msg": str(e)}

    result["found"].sort()
    result["not_found"].sort()
    result["errors"].sort()

    return result


if __name__ == "__main__":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        print('{"error": "missing argument"}')
        sys.exit(1)
    _res = multiscan(sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
