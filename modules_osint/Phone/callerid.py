import json
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == "nt":
    os.system("chcp 65001 >nul")


def callerid_lookup(phone: str) -> dict:
    """findwhocallsyou.com — international reverse phone lookup with network/risk data."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "callerid",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        resp = requests.get(
            f"https://www.findwhocallsyou.com/{clean}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            impersonate="chrome120",
            timeout=15,
            allow_redirects=True,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract text lines (structure: label line followed by value line)
            body_text = soup.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]

            # Parse labeled sections using icon-label → value pattern
            # "📍 Location" → next non-empty line is the value
            # "📶 Network" → next line is carrier
            # "🔍 Total Searches" → next line is count
            label_map = {
                "location": None,
                "network": None,
                "risk": None,
                "searches": None,
                "first_seen": None,
                "last_searched": None,
            }

            for i, line in enumerate(lines):
                lo = line.lower()
                nxt = lines[i + 1] if i + 1 < len(lines) else ""

                if "location" in lo and len(lo) < 20:
                    if nxt and len(nxt) < 60 and nxt not in ("Location",):
                        label_map["location"] = nxt

                elif "network" in lo and len(lo) < 20:
                    if nxt and len(nxt) < 60:
                        label_map["network"] = nxt

                elif "total searches" in lo or ("searches" in lo and len(lo) < 25):
                    # value is the digit on the next line
                    if nxt and re.match(r'^\d+', nxt):
                        label_map["searches"] = int(re.search(r'\d+', nxt).group())

                elif "risk" in lo and "probability" not in lo and len(lo) < 15:
                    # e.g. "0%" on next line
                    pct_m = re.search(r'(\d+)%', nxt)
                    if pct_m:
                        label_map["risk"] = int(pct_m.group(1))

                elif "first seen" in lo and len(lo) < 20:
                    if nxt and len(nxt) < 40:
                        label_map["first_seen"] = nxt

                elif "last searched" in lo and len(lo) < 25:
                    if nxt and len(nxt) < 40:
                        label_map["last_searched"] = nxt

            # Risk score / rating from heading or text
            risk_m = re.search(r'(Low|Medium|High|Critical)[- ]?Risk', html, re.IGNORECASE)
            if risk_m:
                return_data["risk_level"] = risk_m.group(0).strip()

            if label_map["location"] and label_map["location"] not in ("Non-Geographic", "Unknown", "Location"):
                return_data["location"] = label_map["location"]

            if label_map["network"] and label_map["network"] not in ("Unallocated / Invalid", "Unknown", "Network"):
                return_data["carrier"] = label_map["network"]
            elif label_map["network"]:
                return_data["network_status"] = label_map["network"]

            if label_map["risk"] is not None:
                return_data["risk_score_pct"] = label_map["risk"]

            if label_map["searches"]:
                return_data["total_searches"] = label_map["searches"]

            if label_map["first_seen"]:
                return_data["first_seen"] = label_map["first_seen"]

            # reports count
            rep_m = re.search(r'(\d+)\s+(?:report|complaint|comment)', html, re.IGNORECASE)
            if rep_m:
                return_data["reports_count"] = int(rep_m.group(1))

            # safety rating from JSON-LD
            rating_m = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html)
            if rating_m:
                return_data["safety_rating"] = float(rating_m.group(1))

            result["result"] = "found"
            result["return"] = {k: v for k, v in return_data.items() if v is not None}

        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "no_data"}
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
    _res = callerid_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
