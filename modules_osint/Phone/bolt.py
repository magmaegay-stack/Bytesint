import json
import os
from datetime import datetime, timezone
from curl_cffi import requests

if os.name == "nt":
    os.system("chcp 65001 >nul")


def bolt_lookup(phone: str) -> dict:
    """Bolt (ride-sharing) — phone lookup extracts account data."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "bolt",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    country_code = "1"
    national = clean.lstrip("+")
    try:
        import phonenumbers
        pn = phonenumbers.parse(clean, None)
        country_code = str(pn.country_code)
        national = str(pn.national_number)
    except Exception:
        pass

    try:
        s = requests.Session(impersonate="chrome120")

        # Bolt passenger app login — phone step
        resp = s.post(
            "https://node.bolt.eu/user/login/phone",
            headers={
                "User-Agent": "Bolt/CA.18.1 CFNetwork/1492.0.1 Darwin/23.3.0",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "bolt-country-id": "gb",
            },
            json={
                "phone": clean,
                "country_calling_code": f"+{country_code}",
                "device_id": "osint-probe",
                "version": "CA.18.1",
            },
            timeout=20,
        )

        return_data = {"phone": clean}

        if resp.status_code == 200:
            data = resp.json()
            # Bolt returns {"data": {"user_id": ..., "phone": ..., "status": ...}, "code": 0}
            inner = data.get("data") or data
            user_id = inner.get("user_id") or inner.get("userId") or inner.get("id")
            status = inner.get("status") or inner.get("account_status")
            name = inner.get("full_name") or inner.get("name") or inner.get("fullName")
            email = inner.get("email")
            avatar = inner.get("picture") or inner.get("avatar")

            if user_id or status:
                if user_id:
                    return_data["account_id"] = user_id
                if status:
                    return_data["account_status"] = status
                if name:
                    return_data["display_name"] = name
                if email:
                    return_data["masked_email"] = email
                if avatar:
                    return_data["avatar_url"] = avatar
                return_data["registered"] = True
                return_data["status"] = "account_found"
                result["result"] = "found"
            elif data.get("code") == 0 or data.get("message"):
                # OTP sent — account confirmed
                return_data["registered"] = True
                return_data["status"] = "otp_requested"
                result["result"] = "found"
            else:
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
                return result

            result["return"] = {k: v for k, v in return_data.items() if v is not None}

        elif resp.status_code == 400:
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            msg = str(data.get("message") or data.get("error") or "").lower()
            if "not found" in msg or "no user" in msg or "not exist" in msg:
                result["result"] = "not_found"
                result["return"] = {"status": "not_registered"}
            else:
                result["result"] = "error"
                result["msg"] = msg or f"HTTP {resp.status_code}"

        elif resp.status_code == 404:
            result["result"] = "not_found"
            result["return"] = {"status": "not_registered"}

        elif resp.status_code == 429:
            result["result"] = "error"
            result["msg"] = "rate_limited"

        else:
            # Try passenger API alternative
            resp2 = s.post(
                "https://user.live.boltsvc.net/user/login/phone",
                headers={
                    "User-Agent": "okhttp/4.9.2",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"phone": clean, "country_code": f"+{country_code}"},
                timeout=20,
            )
            if resp2.status_code == 200:
                d2 = resp2.json()
                inner = d2.get("data") or d2
                if inner.get("user_id") or inner.get("status"):
                    return_data["registered"] = True
                    return_data["status"] = "otp_requested"
                    if inner.get("user_id"):
                        return_data["account_id"] = inner["user_id"]
                    result["result"] = "found"
                    result["return"] = return_data
                else:
                    result["result"] = "error"
                    result["msg"] = f"HTTP {resp.status_code}"
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
    _res = bolt_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
