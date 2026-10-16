import sys
import requests
import json
import re
import datetime

def check(username):
    url = f"https://medal.tv/u/{username}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        return { "taken": False, "error": str(e), "ExtraData": {} }

    if response.status_code == 404:
        return { "taken": False, "ExtraData": {} }
    
    if response.status_code != 200:
        return { "taken": False, "ExtraData": {} }

    html_content = response.text

    match = re.search(r'var hydrationData\s*=\s*(\{.*?\})(?:;|</script>)', html_content)

    if not match:
        return { "taken": False, "ExtraData": {} }

    try:
        json_str = match.group(1)
        data = json.loads(json_str)
        
        profiles = data.get('profiles', {})
        
        if not profiles:
            return { "taken": False, "ExtraData": {} }

        user_id = next(iter(profiles))
        user = profiles[user_id]
        
        if user.get('userName', '').lower() != username.lower():
             pass 

        joined = None
        if user.get('createdAt'):
            try:
                joined = datetime.datetime.fromtimestamp(user['createdAt'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            except: pass

        return {
            "taken": True,
            "ExtraData": {
                "Nickname": user.get('displayName'),
                "Username": user.get('userName'),
                "UserID": user.get('userId'),
                "Bio": user.get('slogan'),
                "Followers": user.get('followers'),
                "Following": user.get('following'),
                "Upvotes": user.get('upvotes'),
                "Joined": joined,
                "Premium": user.get('premiumType', 'NONE') != 'NONE',
                "Status": user.get('status'),
                "ProfilePicUrl": user.get('thumbnail'),
                "CoverPicUrl": user.get('coverPhoto'),
                "ProfileUrl": f"https://medal.tv/u/{user.get('userName')}"
            }
        }

    except Exception as e:
        return {
            "taken": False, 
            "error": f"Parsing error: {str(e)}", 
            "ExtraData": {}
        }

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = check(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
