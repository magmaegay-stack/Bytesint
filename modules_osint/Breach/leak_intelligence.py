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
        return {"stealers_count": 0, "malware_families": [], "compromised": False, "details": []}
    
    stealers = data.get("stealers") or []
    count = data.get("total") or len(stealers)
    families = set()
    cleaned_stealers = []

    for s in stealers:
        if isinstance(s, dict):
            fam = s.get("stealer_family") or s.get("malware") or "Infostealer"
            families.add(fam)
            cleaned_stealers.append({
                "date": s.get("date_compromised", "Unknown"),
                "computer_name": s.get("computer_name", "Unknown PC"),
                "operating_system": s.get("operating_system", "Unknown OS"),
                "services_compromised": s.get("total_user_services", 0),
                "corporate_services": s.get("total_corporate_services", 0),
                "malware_family": fam,
                "malware_path": s.get("malware_path", "N/A"),
                "masked_logins": [x for x in (s.get("top_logins") or []) if x][:5],
            })
    
    return {
        "stealers_count": count,
        "malware_families": list(families),
        "compromised": count > 0,
        "details": cleaned_stealers
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
                "date": s.get("date") or "Undisclosed"
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

def check_hackertarget_geoip(target: str) -> dict:
    ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    if not re.match(ip_pattern, target):
        return None
    try:
        req = urllib.request.Request(f"https://api.hackertarget.com/geoip/?q={target}", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8")
            res = {}
            for line in text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    res[k.strip().lower()] = v.strip()
            return res
    except Exception:
        return None

def leak_osint(target: str) -> dict:
    clean = target.strip()
    is_email = "@" in clean and "." in clean
    
    # 1. Check IP Shodan & HackerTarget
    shodan_res = check_shodan_internetdb(clean)
    geoip_res = check_hackertarget_geoip(clean)
    
    # 2. Check Hudson Rock (Info-stealers)
    hudson_res = check_hudson_rock(clean, is_email)
    
    # 3. Check LeakCheck (Breach databases)
    leakcheck_res = check_leakcheck(clean)
    
    stealer_list = hudson_res.get("details", [])
    breach_list = leakcheck_res.get("sources", [])
    
    total_breaches = len(stealer_list) + len(breach_list)
    is_found = total_breaches > 0 or (shodan_res is not None and len(shodan_res.get("ports", [])) > 0)
    
    threat_score = min(100, (len(stealer_list) * 25) + (len(breach_list) * 8))
    
    sources_summary = [s["name"] for s in breach_list[:10]]
    if hudson_res.get("malware_families"):
        sources_summary.extend([f"Infostealer ({m})" for m in hudson_res.get("malware_families")])
    
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
            "geoip": geoip_res,
            "stealer_logs": stealer_list,
            "breach_sources": breach_list,
            "sources_summary": sources_summary,
            "status": f"{total_breaches} Violazioni / Stealer rilevati" if is_found else "Nessuna violazione pubblica rilevata"
        }
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('{"error": "missing target query"}')
        sys.exit(1)
    res = leak_osint(sys.argv[1].strip())
    print(json.dumps(res, indent=4, ensure_ascii=False))
