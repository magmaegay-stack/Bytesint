import sys
import json
import io
import os
import re
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

if os.name == 'nt':
    os.system('chcp 65001 >nul')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# COOKIE DI SESSIONE AUTENTICATI
# ==========================================
MANUAL_COOKIES = {
    "li_at": "AQEDAWVUUIMElnCKAAABoOH8CTcAAAGhBgiNN04AxGvdOBXFrqZQUc5vA_D47PlZdIXtfdlh_X7icaXay95d-P21gXpgBjcRXcexPUuc0NiIjt9Asl578y2hVblzXSrUphKljEtjp1vzb-cAyU7nwfDr",
    "JSESSIONID": "ajax:-8319197758734463832",
    "lidc": "b=TB51:s=T:r=T:a=T:p=T:g=5446:u=9:x=1:i=1790497786:t=1790584028:v=2:sig=AQFMjNM-fy-D5C2wmOa-RvPldK1k2gej",
    "bscookie": "v=1&202603042042469ccbc311-0276-4eec-8106-45b10456c25cAQFgX-zUElEVTfU-YDT_M194VlELZttj"
}

def parse_job_and_company(headline: str):
    if not headline or headline == "N/D":
        return "N/D", "N/D"
    match = re.search(r"(.+?)\s+(?:at|@|presso|–|-)\s+(.*)", headline, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return headline, "N/D"

def linkedin_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    
    result = {
        "target": clean_target,
        "service": "linkedin",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    active_cookies = {k: v.strip('"\'') for k, v in MANUAL_COOKIES.items() if v.strip()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }

    try:
        response = None
        valid_url = ""
        is_company = False
        
        # Test 1: Profilo Personale (/in/)
        url_in = f"https://www.linkedin.com/in/{clean_target}"
        resp_in = requests.get(url_in, headers=headers, cookies=active_cookies, impersonate="chrome120", timeout=12, allow_redirects=True)
        
        if resp_in.status_code == 200 and "authwall" not in resp_in.url.lower():
            response = resp_in
            valid_url = resp_in.url
            is_company = False
        else:
            # Test 2: Pagina Aziendale (/company/)
            url_co = f"https://www.linkedin.com/company/{clean_target}"
            resp_co = requests.get(url_co, headers=headers, cookies=active_cookies, impersonate="chrome120", timeout=12, allow_redirects=True)
            if resp_co.status_code == 200 and "authwall" not in resp_co.url.lower():
                response = resp_co
                valid_url = resp_co.url
                is_company = True

        if not response or response.status_code != 200:
            result["return"] = {"identifier": clean_target, "status": "not_found", "http_status": 404}
            return result

        soup = BeautifulSoup(response.text, 'html.parser')
        
        profile_name = "N/D"
        job_title = "N/D"
        company = "N/D"
        bio = "no bio"
        profile_image = "N/D"
        headline = "N/D"

        # 1. Estrazione Nome da OpenGraph (prioritario e sicuro)
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            profile_name = og_title.get("content").strip()
        elif soup.title:
            profile_name = soup.title.get_text().strip()

        if profile_name and profile_name != "N/D":
            profile_name = re.sub(r'\s*\|\s*LinkedIn.*$', '', profile_name, flags=re.IGNORECASE).strip()

        # Estrazione Descrizione / Bio
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc_val = og_desc.get("content").strip()
            if desc_val and "View " not in desc_val:
                bio = desc_val

        # Estrazione Immagine
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            profile_image = og_img.get("content").strip()

        # JSON-LD di supporto
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld and json_ld.string:
            try:
                ld_data = json.loads(json_ld.string)
                if isinstance(ld_data, list):
                    ld_data = ld_data[0]
                if (not profile_name or profile_name == "N/D") and "name" in ld_data:
                    profile_name = ld_data.get("name", "").strip()
                if bio == "no bio" and "description" in ld_data:
                    bio = ld_data.get("description", "").strip()
                if not is_company and "jobTitle" in ld_data:
                    job_title = ld_data.get("jobTitle", "N/D")
            except Exception:
                pass

        if is_company:
            company = profile_name
            job_title = "Organization / Company Page"
            if not profile_name or profile_name == "N/D":
                profile_name = clean_target.capitalize()
                company = profile_name
        else:
            headline_elem = soup.find(class_=lambda x: x and "text-body-medium" in x)
            if headline_elem:
                headline = headline_elem.get_text().strip()
            
            parsed_job, parsed_company = parse_job_and_company(headline)
            if job_title == "N/D":
                job_title = parsed_job
            company = parsed_company

        result["result"] = "found"
        
        # Struttura di ritorno pulita: inserisce sempre il profile_name e rimuove i campi vuoti o N/D
        return_data = {
            "identifier": clean_target,
            "profile_name": profile_name,
            "profile_url": valid_url,
            "status": "verified_active",
            "http_status": response.status_code
        }

        if job_title and job_title != "N/D":
            return_data["job_title"] = job_title
        if company and company != "N/D":
            return_data["company"] = company
        if bio and bio != "no bio":
            return_data["bio"] = bio
        if profile_image and profile_image != "N/D":
            return_data["profile_image"] = profile_image

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
    _res = parse_job_and_company(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
