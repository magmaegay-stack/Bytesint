#!/usr/bin/env python3
import sys
import os
import json
import re
import urllib.request
from datetime import datetime, timezone

def fetch_json(url: str, timeout: int = 6):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
    return None

def check_hudson_rock(target: str, is_email: bool) -> dict:
    endpoint = f"https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email?email={urllib.request.quote(target)}" if is_email \
        else f"https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-username?username={urllib.request.quote(target)}"
    
    data = fetch_json(endpoint, timeout=6)
    if not data or not isinstance(data, dict):
        return {"stealers_count": 0, "malware_families": [], "compromised": False}
    
    stealers = data.get("stealers") or []
    count = data.get("total") or len(stealers)
    families = set()
    for s in stealers:
        if isinstance(s, dict):
            fam = s.get("stealer_family") or s.get("malware")
            if fam:
                families.add(fam)
    
    return {
        "stealers_count": count,
        "malware_families": list(families),
        "compromised": count > 0,
        "details": stealers[:5]
    }

def check_leakcheck(target: str) -> dict:
    url = f"https://leakcheck.io/api/public?check={urllib.request.quote(target)}"
    data = fetch_json(url, timeout=6)
    if not data or not isinstance(data, dict):
        return {"sources_count": 0, "sources": [], "found": False}
    
    success = data.get("success", False)
    sources = data.get("sources") or []
    
    cleaned_sources = []
    for s in sources:
        if isinstance(s, dict):
            cleaned_sources.append({
                "name": s.get("name", "Unknown Source"),
                "date": s.get("date", "Undisclosed")
            })
    
    return {
        "sources_count": len(cleaned_sources),
        "sources": cleaned_sources,
        "found": success and len(cleaned_sources) > 0
    }

def check_shodan_internetdb(target: str) -> dict:
    ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    if not re.match(ip_pattern, target):
        return None
    url = f"https://internetdb.shodan.io/{target}"
    data = fetch_json(url, timeout=5)
    if not data or not isinstance(data, dict):
        return None
    return {
        "ip": data.get("ip"),
        "hostnames": data.get("hostnames", []),
        "ports": data.get("ports", []),
        "cves": data.get("cves", []),
        "tags": data.get("tags", []),
        "vulns": data.get("vulns", [])
    }

def leak_osint(target: str) -> dict:
    clean = target.strip()
    is_email = "@" in clean and "." in clean
    
    # 1. Check IP Shodan
    shodan_res = check_shodan_internetdb(clean)
    
    # 2. Check Hudson Rock (Info-stealers)
    hudson_res = check_hudson_rock(clean, is_email)
    
    # 3. Check LeakCheck (Breach databases)
    leakcheck_res = check_leakcheck(clean)
    
    total_breaches = (hudson_res.get("stealers_count", 0)) + (leakcheck_res.get("sources_count", 0))
    is_found = total_breaches > 0 or (shodan_res is not None and len(shodan_res.get("ports", [])) > 0)
    
    threat_score = min(100, (hudson_res.get("stealers_count", 0) * 25) + (leakcheck_res.get("sources_count", 0) * 15))
    
    sources_list = [s["name"] for s in leakcheck_res.get("sources", [])[:8]]
    if hudson_res.get("malware_families"):
        sources_list.extend([f"Infostealer: {m}" for m in hudson_res.get("malware_families")])
    
    return {
        "target": clean,
        "service": "leak_intelligence",
        "result": "found" if is_found else "not_found",
        "return": {
            "is_breached": is_found,
            "total_records": total_breaches,
            "threat_score": threat_score,
            "hudson_rock": hudson_res,
            "leakcheck": leakcheck_res,
            "shodan": shodan_res,
            "breach_sources": sources_list,
            "status": "Compromised Records Found" if is_found else "Safe / Zero Public Breaches"
        }
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('{"error": "missing target query"}')
        sys.exit(1)
    res = leak_osint(sys.argv[1].strip())
    print(json.dumps(res, indent=4, ensure_ascii=False))
