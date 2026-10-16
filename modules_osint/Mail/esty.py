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

def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))

def etsy_lookup(target: str) -> dict:
    clean_target = target.strip()
    is_email = validate_email(clean_target)
    
    result = {
        "target": clean_target,
        "type": "email" if is_email else "username",
        "service": "etsy",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "unknown",
        "profile": {}
    }

    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en:q=0.7",
        "Referer": "https://www.etsy.com/"
    }

    try:
        # Estraiamo la parte prima della chiocciola se è un'email, altrimenti usiamo la stringa pulita
        query_slug = clean_target.split("@")[0] if is_email else clean_target.lstrip("@")
        profile_url = f"https://www.etsy.com/people/{query_slug}"

        response = session.get(profile_url, headers=headers, impersonate="chrome120", timeout=10)

        if response.status_code == 200:
            html = response.text
            
            # Se la pagina esiste e non è una pagina di errore custom di Etsy
            if "Uh oh!" not in html and ("profile" in html or "follower" in html):
                result["result"] = "found"
                
                # Estrazione dati tramite regex pulite dal corpo HTML
                username_match = re.search(r'"username"\s*:\s*"([^"]+)"', html)
                joined_match = re.search(r'isMemberSince["\']?\s*:\s*["\']?([^"\']+)', html)
                
                result["profile"] = {
                    "username": f"@{username_match.group(1)}" if username_match else f"@{query_slug}",
                    "email": clean_target if is_email else "N/D",
                    "followers": "Verificato",
                    "following": "Verificato",
                    "joined_date": joined_match.group(1) if joined_match else "Disponibile su profilo",
                    "profile_url": profile_url,
                    "http_status": response.status_code
                }
            else:
                result["result"] = "not_found"
                result["profile"] = {
                    "note": "Nessun profilo pubblico attivo trovato per questa identità.",
                    "http_status": response.status_code
                }
        elif response.status_code == 404:
            result["result"] = "not_found"
            result["profile"] = {
                "note": "Profilo inesistente (HTTP 404).",
                "http_status": 404
            }
        else:
            result["result"] = "protected"
            result["profile"] = {
                "note": "Accesso limitato o bloccato dal WAF di Etsy.",
                "http_status": response.status_code
            }

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = validate_email(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
