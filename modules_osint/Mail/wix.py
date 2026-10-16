import sys
import asyncio
import aiohttp
import json

class BaseModule:
    def __init__(self, session):
        self.session = session

class WixModule(BaseModule):
    def __init__(self, session):
        super().__init__(session)
        self.website = "wix.com"

    async def check(self, email: str):
        try:
            signin_url = "https://users.wix.com/signin"
            async with self.session.get(signin_url) as resp1:
                if resp1.status != 200:
                    return None
            
            xsrf_cookie = next((cookie for cookie in self.session.cookie_jar if cookie.key == 'XSRF-TOKEN'), None)
            if not xsrf_cookie:
                return None
            
            xsrf_token = xsrf_cookie.value

            api_url = "https://users.wix.com/wix-users/v1/userAccountsByEmail"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'origin': 'https://users.wix.com',
                'referer': signin_url,
                'x-wix-client-artifact-id': 'login-react-app',
                'x-xsrf-token': xsrf_token,
            }
            payload = {'email': email}

            async with self.session.post(api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    result = {
                        "accountId": data.get("accountId"),
                        "emailVerified": data.get("emailVerified"),
                        "isBlocked": data.get("isBlocked"),
                        "userAuthenticatorsData": data.get("userAuthenticatorsData"),
                    }
                    final_data = {k: v for k, v in result.items() if v is not None}
                    
                    if not final_data:
                        return {"registered": True}
                    
                    return final_data
                
                return None
        
        except Exception as e:
            return None

async def main():
    if len(sys.argv) < 2:
        return
    
    email = sys.argv[1]
    
    # Usiamo un CookieJar esplicito per catturare l'XSRF-TOKEN
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
        module = WixModule(session)
        result = await module.check(email)
        print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())