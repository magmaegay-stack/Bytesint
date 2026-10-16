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

def telegram_lookup(target: str) -> dict:
    clean_target = target.strip().lstrip('@')
    url = f"https://t.me/{clean_target}"
    
    result = {
        "target": clean_target,
        "service": "telegram",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        
        if response.status_code != 200:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        soup = BeautifulSoup(response.text, "html.parser")
        
        title_tag = soup.find("meta", property="og:title")
        desc_tag = soup.find("meta", property="og:description")
        image_tag = soup.find("meta", property="og:image")

        if not title_tag:
            result["result"] = "not_found"
            result["return"] = {"status": "not_exists"}
            return result

        display_name = title_tag.get("content", "").strip()
        
        return_data = {
            "username": clean_target,
            "display_name": display_name,
            "profile_url": url,
            "status": "verified_active"
        }

        if desc_tag:
            bio = desc_tag.get("content", "").strip()
            if bio:
                return_data["bio"] = bio

        if image_tag:
            avatar_url = image_tag.get("content", "").strip()
            if avatar_url:
                return_data["avatar_url"] = avatar_url

        # Ricerca di eventuali link esterni o menzioni nel testo della pagina profilo
        page_text = soup.get_text()
        if "t.me/" in page_text:
            # Estrazione di link correlati presenti nella descrizione visibile
            extra_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("https://t.me/") and clean_target not in href:
                    extra_links.append(href)
            if extra_links:
                return_data["related_links"] = list(set(extra_links))

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
    _res = telegram_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
