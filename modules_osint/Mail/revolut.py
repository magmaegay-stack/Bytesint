import sys
import json
import io
import os
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == 'nt':
    os.system('chcp 65001 >nul')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def revolut_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    url = f"https://revolut.me/{clean_target}"
    
    result = {
        "target": clean_target,
        "service": "revolut.me",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(
            url, 
            headers=headers, 
            impersonate="chrome120", 
            timeout=15, 
            allow_redirects=True
        )
        
        if response.status_code != 200:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        error_phrases = [
            "We can’t find that one",
            "We can't find that one",
            "The link you followed may be broken or may have been removed"
        ]
        
        if any(phrase in page_text for phrase in error_phrases):
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        if "How much do you want to send?" not in page_text and len(clean_target) <= 2:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        extracted_name = None

        h1_tag = soup.find("h1")
        if h1_tag:
            span_tag = h1_tag.find("span", attrs={"max": "3"})
            if span_tag:
                candidate = span_tag.get_text().strip()
                if candidate and candidate.lower() not in ["revolut", "revolut.me", ""]:
                    extracted_name = candidate

        if not extracted_name:
            name_span = soup.find("span", attrs={"max": "3"})
            if name_span:
                candidate = name_span.get_text().strip()
                if candidate and candidate.lower() not in ["revolut", "revolut.me", ""]:
                    extracted_name = candidate


        if not extracted_name:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                candidate = og_title.get("content").strip()
                if candidate and "revolut" not in candidate.lower():
                    extracted_name = candidate

        return_data = {
            "profile_url": response.url,
            "status": "verified_active"
        }

        if extracted_name:
            return_data["profile_name"] = extracted_name

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
    _res = revolut_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
