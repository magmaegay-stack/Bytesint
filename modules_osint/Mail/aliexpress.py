"""
aliexpress_full.py
==================
Modulo unificato AliExpress:

  fetch(value, lookup_type)
      → cerca per email/telefono
      → se trova userId, arricchisce automaticamente con il profilo social/UGC completo
      → restituisce un dict con 'show', 'full', 'social_profile'

  fetch_social_profile(numeric_member_seq)
      → accesso diretto al profilo UGC dato un member_seq numerico
"""

import hashlib
import time
import json
import os
import sys
import logging
import asyncio

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
import re
from typing import Optional

import httpx
import phonenumbers

# ---------------------------------------------------------------------------
# Costanti globali
# ---------------------------------------------------------------------------
DOMAIN = "aliexpress.com"
TARGET_TYPES = ["email", "phone"]

TOKEN_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    f"{DOMAIN.split('.')[0]}_token.json",
)

logging.basicConfig()
logger = logging.getLogger("AliexpressClient")

APP_KEY          = "21371581"
APP_KEY_LOGIN    = "12574478"
APP_KEY_SOCIAL   = "24815441"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)

REFERER_EMAIL  = "https://www.aliexpress.com/p/account-center2/new-email-find-account.html"
REFERER_PHONE  = "https://www.aliexpress.com/p/account-center2/new-phone-find-account.html"
REFERER_LOGIN  = "https://login.aliexpress.com/"
ORIGIN_LOGIN   = "https://login.aliexpress.com"

MTOP_EMAIL_URL            = "https://acs.aliexpress.com/h5/mtop.aliexpress.member.member.center.finddesmeminfolist/1.0/"
MTOP_PHONE_SUFFIX_URL     = "https://acs.aliexpress.com/h5/mtop.aliexpress.member.member.center.phonesuffix/1.0/"
MTOP_GET_USER_BY_TOKEN_URL= "https://acs.aliexpress.com/h5/mtop.global.user.getuserbytoken/1.0/"
MTOP_IDENTITY_INIT_URL    = "https://acs.aliexpress.com/h5/mtop.global.user.identity.init/1.0/"
UMID_URL                  = "https://us.ynuf.aliapp.org/service/um.json"

ACS_BASE       = "https://acs.aliexpress.com/h5/"
API_BASE_INFO  = "mtop.aliexpress.ugc.feed.member.baseInfo"
URL_BASE_INFO  = f"{ACS_BASE}{API_BASE_INFO}/1.0/"
STAR_HOME      = "https://star.aliexpress.com/"
STAR_PROFILE_BASE = "https://star.aliexpress.com/m/profile/backflow/"
STAR_ORIGIN    = "https://star.aliexpress.com"

# Chiavi in cui può comparire il bizToken nelle response
BIZ_TOKEN_KEYS = (
    "bizToken", "biz_token", "verifyToken", "verificationToken",
    "verification_token", "token", "findAccountToken",
)

# Pattern "utente non esistente" nei ret
RET_NOT_FOUND_PATTERNS = (
    "USER-NOT-EXISTED", "USER_NOT_EXISTED",
    "USER-NOT-EXIST",  "USER_NOT_EXIST",
    "ACCOUNT-NOT-EXIST","ACCOUNT_NOT_EXIST",
    "NOT_EXISTED", "NOT EXISTED",
    "NOT_FOUND",   "NOT FOUND",
)

# Pattern rate-limit nei ret
RET_RATE_LIMIT_PATTERNS = (
    "FAIL_SYS_TRAFFIC_LIMIT",
    "RATE_LIMIT", "RATELIMIT",
    "TOO-MANY",   "TOO_MANY",
    "FREQUENCY",
)

ESSENTIAL_COOKIES = {
    "cna", "_m_h5_tk", "_m_h5_tk_enc",
    "acs_usuc_t", "ali_apache_id", "isg", "tfstk",
}

# ---------------------------------------------------------------------------
# Utility generiche
# ---------------------------------------------------------------------------

def ret_matches(ret_messages, patterns) -> bool:
    """True se almeno un messaggio in ret contiene uno dei pattern (case-insens.)."""
    if not ret_messages:
        return False
    upper = [str(m).upper() for m in ret_messages]
    return any(p.upper() in m for p in patterns for m in upper)


def reset_token_file(token_file: str = TOKEN_FILE) -> None:
    """Elimina il file token per partire da uno stato pulito."""
    try:
        if os.path.exists(token_file):
            os.remove(token_file)
            logger.info(f"[RESET] Token file eliminato: {token_file}")
        else:
            logger.debug(f"[RESET] Token file non presente: {token_file}")
    except Exception as e:
        logger.warning(f"[RESET] Impossibile eliminare token file: {e}")


def load_tokens() -> dict:
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def build_telemetry(now_ms: int, referer: str) -> dict:
    return {
        "ua":           f"defaultUA1_uab_not_loaded@@{referer}@@{now_ms}",
        "umidToken":    f"defaultToken1_um_not_loaded@@{referer}@@{now_ms - 2003}",
        "bx-ua":        f"defaultFY2_load_failed with timeout@@{referer}@@{now_ms + 2}",
        "bx-umidtoken": f"defaultFY2_load_failed with timeout@@{referer}@@{now_ms + 2}",
    }


# ---------------------------------------------------------------------------
# Phone parsing
# ---------------------------------------------------------------------------

def parse_phone_value(value: str, default_region: Optional[str] = None) -> str:
    """Converte un numero di telefono nel formato 'cc-national_number'."""
    value = (value or "").strip()
    if not value:
        return value

    # Già nel formato cc-number?
    if "-" in value and not value.startswith("+"):
        cc_part, _, nn_part = value.partition("-")
        cc_part = cc_part.lstrip("+")
        if cc_part.isdigit() and nn_part.isdigit():
            try:
                n = phonenumbers.parse("+" + cc_part + nn_part, default_region)
                if phonenumbers.is_possible_number(n):
                    return f"{n.country_code}-{n.national_number}"
            except phonenumbers.NumberParseException:
                pass
        return value

    candidate = value if value.startswith("+") else "+" + value.lstrip("0")
    try:
        n = phonenumbers.parse(candidate, default_region)
        if phonenumbers.is_possible_number(n):
            return f"{n.country_code}-{n.national_number}"
    except phonenumbers.NumberParseException as e:
        logger.debug(f"[PHONE] phonenumbers parse error per {value!r}: {e}")

    raw = value[1:] if value.startswith("+") else value
    if len(raw) > 10:
        cc     = raw[:-10]
        number = raw[len(cc):]
        return f"{cc}-{number}"
    return raw


def split_identity_input(passport: str, lookup_type: str) -> tuple:
    """Scompone il passport in (login_name, login_name_type, login_name_prefix)."""
    if lookup_type == "email":
        return passport.strip(), "EMAIL", None

    raw       = (passport or "").strip()
    candidate = raw if raw.startswith("+") else "+" + raw.lstrip("0")
    try:
        n = phonenumbers.parse(candidate, None)
        if phonenumbers.is_possible_number(n):
            return str(n.national_number), "PHONE", str(n.country_code)
    except phonenumbers.NumberParseException:
        pass

    if "-" in raw:
        cc, _, nn = raw.partition("-")
        cc = cc.lstrip("+")
        if cc.isdigit() and nn.isdigit():
            return nn, "PHONE", cc

    return raw.lstrip("+"), "PHONE", ""


# ---------------------------------------------------------------------------
# Safe HTTP helpers
# ---------------------------------------------------------------------------

async def safe_get(session, url, headers=None, timeout=15.0, **kwargs):
    try:
        return await session.get(url, headers=headers, timeout=timeout, **kwargs)
    except TypeError:
        pass
    try:
        return await session.get(url, headers=headers, **kwargs)
    except TypeError:
        pass
    return await session.get(url)


async def safe_post(session, url, params=None, headers=None, data=None, timeout=30.0):
    try:
        return await session.post(url, params=params, headers=headers, data=data, timeout=timeout)
    except TypeError:
        pass
    try:
        return await session.post(url, params=params, headers=headers, data=data)
    except TypeError:
        pass
    return await session.post(url, data=data)


# ---------------------------------------------------------------------------
# Cookie helpers (social module)
# ---------------------------------------------------------------------------

def _cookies_dict(client: httpx.AsyncClient) -> dict:
    result = {}
    try:
        for cookie in client.cookies.jar:
            if cookie.name in ESSENTIAL_COOKIES:
                result[cookie.name] = cookie.value
    except Exception:
        for name in ESSENTIAL_COOKIES:
            try:
                v = client.cookies.get(name)
                if v:
                    result[name] = v
            except Exception:
                pass
    return result


def _get_h5_token(client: httpx.AsyncClient) -> str:
    try:
        for cookie in client.cookies.jar:
            if cookie.name == "_m_h5_tk" and "_" in (cookie.value or ""):
                return cookie.value.split("_")[0]
    except Exception:
        pass
    return ""


def _token_expired_social(client: httpx.AsyncClient) -> bool:
    try:
        for cookie in client.cookies.jar:
            if cookie.name == "_m_h5_tk" and "_" in (cookie.value or ""):
                exp = int(cookie.value.split("_")[1])
                return (exp - int(time.time() * 1000)) < 60_000
    except Exception:
        pass
    return True


def _sign_social(token: str, ts: str, app_key: str, data_str: str) -> str:
    return hashlib.md5(f"{token}&{ts}&{app_key}&{data_str}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# Utility response
# ---------------------------------------------------------------------------

def extract_inner(data_block: dict) -> dict:
    nested = data_block.get("data")
    if isinstance(nested, dict) and "code" in nested:
        return nested
    return data_block


def find_biz_token(obj, _depth: int = 0) -> Optional[str]:
    if _depth > 6 or obj is None:
        return None
    if isinstance(obj, dict):
        for k in BIZ_TOKEN_KEYS:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in obj.values():
            found = find_biz_token(v, _depth + 1)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_biz_token(item, _depth + 1)
            if found:
                return found
    return None


def interpret_inner(inner_data: dict) -> Optional[dict]:
    inner_code = inner_data.get("code")
    code_info  = (inner_data.get("codeInfo") or "").lower()

    if inner_code == 245:
        return {"service": DOMAIN, "result": "rate_limit", "msg": code_info}
    if inner_code == 500:
        if "vuoto" in code_info or "empty" in code_info:
            return {"service": DOMAIN, "result": "not_found"}
        return {"service": DOMAIN, "result": "error", "msg": code_info}
    if inner_code == 4 or "not existed" in code_info or "not found" in code_info:
        return {"service": DOMAIN, "result": "not_found"}
    return None


def interpret_identity_init(ubt_inner: dict) -> Optional[dict]:
    if not isinstance(ubt_inner, dict):
        return None
    return {
        "exist":           bool(ubt_inner.get("exist")),
        "token":           ubt_inner.get("token"),
        "page_type":       ubt_inner.get("pageType"),
        "auto_send":       ubt_inner.get("autoSend"),
        "hide_other_ways": ubt_inner.get("hideOtherWays"),
        "error_msg":       ubt_inner.get("errorMsg") or None,
    }


def format_partial_phone(phone: Optional[str], prefix: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    return f"+{prefix} {phone}" if prefix else phone


def format_response(full_output: dict,
                    user_by_token: Optional[dict] = None,
                    identity_init_block: Optional[dict] = None,
                    social_profile: Optional[dict] = None) -> dict:
    """
    Costruisce la struttura finale con esattamente 2 chiavi: 'show' e 'full'.

    show:
      id, name (contact_name dal social, fallback nickName), email, avatar,
      partial_email, login_id, phone, username (nickname dal social),
      exists, page_type

    full:
      returnObject   – lista account raw da findDesMemInfoList
      identity       – risposta grezza di identity.init
      user_by_token  – risposta grezza di getUserByToken
      socialProfile  – profilo UGC completo
    """
    # ── show: base da returnObject ────────────────────────────────────────────
    show_list  = []
    return_obj = full_output.get("returnObject") or []

    if isinstance(return_obj, list):
        for account in return_obj:
            if not isinstance(account, dict):
                continue
            mapping = {
                "id":     account.get("loginId"),
                "name":   account.get("nickName"),
                "email":  account.get("email"),
                "avatar": account.get("portraitPath"),
            }
            cleaned = {k: v for k, v in mapping.items() if v not in (None, "")}
            if cleaned:
                show_list.append(cleaned)

    if len(show_list) == 1:
        show_output = show_list[0]
    elif len(show_list) > 1:
        show_output = len(show_list)
    else:
        show_output = {}

    # ── show: arricchimento via getUserByToken ────────────────────────────────
    if user_by_token and isinstance(user_by_token, dict):
        ubt_data = user_by_token.get("data") or {}
        if isinstance(ubt_data.get("data"), dict):
            ubt_data = ubt_data["data"]

        partial = {
            "id":            ubt_data.get("userId"),
            "email": ubt_data.get("email"),
            "phone":         format_partial_phone(
                                 ubt_data.get("phoneNum"),
                                 ubt_data.get("phonePrefixCode"),
                             ),
            "login_id":      ubt_data.get("loginId"),
        }
        partial = {k: v for k, v in partial.items() if v not in (None, "", [])}

        if partial:
            if isinstance(show_output, dict):
                show_output = {**show_output, **partial}
            elif not isinstance(show_output, int):
                show_output = partial

    # ── show: arricchimento via social_profile ────────────────────────────────
    if social_profile and isinstance(social_profile, dict) and social_profile.get("exists"):
        if isinstance(show_output, dict):
            # username = nickname del profilo social
            nickname = social_profile.get("nickname")
            if nickname:
                show_output["username"] = nickname

            # name → contact_name del social (se presente), altrimenti lascia invariato
            contact_name = social_profile.get("contact_name")
            if contact_name:
                show_output["name"] = contact_name

            # avatar → big_avatar dal social (qualità superiore), fallback a avatar
            big_avatar = social_profile.get("big_avatar") or social_profile.get("avatar")
            if big_avatar:
                show_output["avatar"] = big_avatar

            # location → country dal profilo social
            country = social_profile.get("country")
            if country:
                show_output["location"] = country

    # ── full: struttura pulita con 4 sotto-chiavi fisse ──────────────────────
    full_combined: dict = {}

    # 1. returnObject
    full_combined["returnObject"] = return_obj

    # 2. identity (risposta grezza di identity.init)
    if identity_init_block and isinstance(identity_init_block, dict):
        full_combined["identity"] = identity_init_block

    # 3. user_by_token
    if user_by_token and isinstance(user_by_token, dict):
        full_combined["user_by_token"] = user_by_token

    # 4. socialProfile
    if social_profile and isinstance(social_profile, dict) and social_profile.get("exists"):
        full_combined["socialProfile"] = social_profile

    return {"show": show_output, "full": full_combined}


# ---------------------------------------------------------------------------
# HTTP client factory
# ---------------------------------------------------------------------------

def new_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"user-agent": UA},
    )


# ===========================================================================
# AliexpressClient  (lookup email/phone)
# ===========================================================================

class AliexpressClient:

    def __init__(self, session, token_file: str = TOKEN_FILE):
        self.session    = session
        self.token_file = token_file
        self.app_key    = APP_KEY
        self.state_data = load_tokens()
        cookies = self.state_data.get("cookies", {})
        for k, v in cookies.items():
            if not v:
                continue
            try:
                self.session.cookies.set(k, v, domain=".aliexpress.com")
            except Exception:
                try:
                    self.session.cookies[k] = v
                except Exception:
                    pass

    # ── state ────────────────────────────────────────────────────────────────

    def _save_state(self):
        try:
            session_cookies = dict(self.session.cookies)
            essential = {
                "cna", "_m_h5_tk", "_m_h5_tk_enc",
                "acs_usuc_t", "ali_apache_id", "isg", "tfstk",
            }
            saved  = {k: v for k, v in session_cookies.items() if k in essential}
            merged = {**self.state_data.get("cookies", {}), **saved}
            self.state_data["cookies"] = merged
            with open(self.token_file, "w", encoding="utf-8") as f:
                json.dump(self.state_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Errore salvataggio: {e}")

    # ── token utils ──────────────────────────────────────────────────────────

    def _get_token_from_cookies(self) -> Optional[str]:
        try:
            cookie_val = self.session.cookies.get("_m_h5_tk")
        except Exception:
            cookie_val = None
        if cookie_val and "_" in cookie_val:
            return cookie_val.split("_")[0]
        return None

    def _is_token_expired(self) -> bool:
        try:
            cookie_val = self.session.cookies.get("_m_h5_tk")
            if not cookie_val or "_" not in cookie_val:
                return True
            expiry_ms = int(cookie_val.split("_")[1])
            now_ms    = int(time.time() * 1000)
            return (expiry_ms - now_ms) < 60000
        except Exception:
            return True

    def _calcola_sign(self, token: str, timestamp: str, data_str: str) -> str:
        return hashlib.md5(
            f"{token}&{timestamp}&{self.app_key}&{data_str}".encode("utf-8")
        ).hexdigest()

    def _build_common_headers(self, referer: str) -> dict:
        return {
            "accept":               "application/json",
            "accept-language":      "en-US,en;q=0.9,it;q=0.8",
            "content-type":         "application/x-www-form-urlencoded",
            "origin":               "https://www.aliexpress.com",
            "referer":              "https://www.aliexpress.com/",
            "sec-ch-ua":            '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-mobile":     "?0",
            "sec-ch-ua-platform":   '"Windows"',
            "sec-fetch-dest":       "empty",
            "sec-fetch-mode":       "cors",
            "sec-fetch-site":       "same-site",
            "user-agent":           UA,
        }

    def _build_login_headers(self) -> dict:
        return {
            "accept":               "application/json",
            "accept-language":      "en-US,en;q=0.9,it;q=0.8",
            "content-type":         "application/x-www-form-urlencoded",
            "origin":               ORIGIN_LOGIN,
            "referer":              REFERER_LOGIN,
            "sec-ch-ua":            '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-mobile":     "?0",
            "sec-ch-ua-platform":   '"Windows"',
            "sec-fetch-dest":       "empty",
            "sec-fetch-mode":       "cors",
            "sec-fetch-site":       "same-site",
            "user-agent":           UA,
        }

    def _sign_login(self, timestamp: str, data_str: str) -> str:
        h5_token = self._get_token_from_cookies() or ""
        return hashlib.md5(
            f"{h5_token}&{timestamp}&{APP_KEY_LOGIN}&{data_str}".encode("utf-8")
        ).hexdigest()

    def _login_params(self, api_name: str, sign: str, timestamp: str) -> dict:
        return {
            "jsv":             "2.7.2",
            "appKey":          APP_KEY_LOGIN,
            "t":               timestamp,
            "sign":            sign,
            "v":               "1.0",
            "api":             api_name,
            "url":             api_name,
            "method":          "POST",
            "dataType":        "jsonp",
            "type":            "originaljson",
            "timeout":         "10000",
            "preventFallback": "true",
        }

    def _build_identity_referer(self, login_name: str, login_name_type: str,
                                login_name_prefix: Optional[str] = None) -> str:
        from urllib.parse import urlencode
        qs = {
            "bizSegment":    "BUYER",
            "identityScene": "FIND_ACCOUNT",
            "_lang":         "it_IT",
            "loginName":     login_name,
            "loginNameType": login_name_type,
        }
        if login_name_prefix:
            qs["loginNamePrefix"] = login_name_prefix
        return (
            "https://login.aliexpress.com/user/saas/identity?"
            + urlencode(qs)
            + "#/verification"
        )

    # ── bootstrap ────────────────────────────────────────────────────────────

    async def _bootstrap_cna(self) -> bool:
        if self.session.cookies.get("cna"):
            return True
        logger.info("[BOOTSTRAP] Rigenerazione cookie 'cna'...")
        headers = {
            "user-agent":      UA,
            "accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9,it;q=0.8",
        }
        for url in ("https://www.aliexpress.com/", "https://log.mmstat.com/eg.js"):
            try:
                await safe_get(self.session, url, headers)
                if self.session.cookies.get("cna"):
                    logger.info(f"[BOOTSTRAP] 'cna' ottenuto: {self.session.cookies.get('cna')}")
                    self._save_state()
                    return True
            except Exception as e:
                logger.debug(f"Fallito GET {url}: {e}")
        return False

    async def _bootstrap_new_token(self, page_url: str = MTOP_EMAIL_URL) -> bool:
        logger.info("[BOOTSTRAP] Rigenerazione '_m_h5_tk'...")
        for k in ("_m_h5_tk", "_m_h5_tk_enc"):
            try:
                if k in self.session.cookies:
                    del self.session.cookies[k]
                self.state_data.get("cookies", {}).pop(k, None)
            except Exception:
                pass
        headers = {
            "accept":      "application/json",
            "user-agent":  UA,
            "referer":     "https://www.aliexpress.com/",
            "origin":      "https://www.aliexpress.com",
        }
        try:
            # STEP 1: visita la pagina HTML find-account → pianta _m_h5_tk lato server
            html_headers = {
                "accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "accept-language": "en-US,en;q=0.9,it;q=0.8",
                "user-agent":      UA,
                "referer":         "https://www.aliexpress.com/",
                "sec-fetch-dest":  "document",
                "sec-fetch-mode":  "navigate",
                "sec-fetch-site":  "same-origin",
            }
            for ref_url in (REFERER_EMAIL, REFERER_PHONE):
                try:
                    await safe_get(self.session, ref_url, html_headers, timeout=15.0)
                    if self._get_token_from_cookies():
                        break
                except Exception as e:
                    logger.debug(f"[BOOTSTRAP] visita {ref_url} fallita: {e}")

            # STEP 2: POST fake a MTOP → se ancora manca, forza l'emissione del cookie
            if not self._get_token_from_cookies():
                try:
                    fake_ts = str(int(time.time() * 1000))
                    await safe_post(
                        self.session, page_url,
                        params={
                            "jsv": "2.5.1", "appKey": self.app_key,
                            "t": fake_ts, "sign": "0", "v": "1.0",
                            "type": "originaljson",
                            "api": "mtop.aliexpress.member.member.center.findDesMemInfoList",
                            "dataType": "jsonp",
                        },
                        headers=self._build_common_headers(REFERER_EMAIL),
                        data={"data": "{}"},
                    )
                except Exception as e:
                    logger.debug(f"[BOOTSTRAP] POST fake fallita: {e}")

            # STEP 3: fallback originale — GET nudo all'endpoint MTOP
            if not self._get_token_from_cookies():
                await safe_get(self.session, page_url, headers, timeout=10.0)

            nuovo_token = self._get_token_from_cookies()
            if nuovo_token:
                logger.info(f"[BOOTSTRAP] Nuovo '_m_h5_tk': {nuovo_token}")
                self._save_state()
                return True
            return False
        except Exception as e:
            logger.error(f"[BOOTSTRAP] Errore: {e}")
            return False

    # ── phone flow ───────────────────────────────────────────────────────────

    async def _visit_phone_page(self) -> bool:
        logger.info("[PHONE] Visita pagina phone per aggiornare token...")
        headers = {
            "accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9,it;q=0.8",
            "user-agent":      UA,
            "referer":         "https://www.aliexpress.com/",
            "sec-fetch-dest":  "document",
            "sec-fetch-mode":  "navigate",
            "sec-fetch-site":  "same-origin",
        }
        try:
            await safe_get(self.session, REFERER_PHONE, headers, timeout=15.0)
            token = self._get_token_from_cookies()
            logger.info(f"[PHONE] Token dopo visita pagina: {token}")
            self._save_state()
            return True
        except Exception as e:
            logger.error(f"[PHONE] Errore visita pagina: {e}")
            return False

    async def _phone_suffix_init(self) -> bool:
        logger.info("[PHONE] phoneSuffix init...")
        now_ms     = int(time.time() * 1000)
        timestamp  = str(now_ms)
        data_payload = {"lang": "it_IT"}
        data_str   = json.dumps(data_payload, separators=(",", ":"))
        token      = self._get_token_from_cookies() or ""
        sign       = self._calcola_sign(token, timestamp, data_str)

        params = {
            "jsv":      "2.5.1",
            "appKey":   self.app_key,
            "t":        timestamp,
            "sign":     sign,
            "v":        "1.0",
            "type":     "originaljson",
            "api":      "mtop.aliexpress.member.member.center.phoneSuffix",
            "dataType": "jsonp",
        }
        form_data = {"data": data_str}

        try:
            response = await safe_post(
                self.session, MTOP_PHONE_SUFFIX_URL,
                params=params,
                headers=self._build_common_headers(REFERER_PHONE),
                data=form_data,
            )
            res_json = response.json()
            ret      = res_json.get("ret", [])
            logger.info(f"[PHONE] phoneSuffix init ret: {ret}")
            self._save_state()
            return any("SUCCESS" in r for r in ret)
        except Exception as e:
            logger.error(f"[PHONE] phoneSuffix init errore: {e}")
            return False

    async def _fetch_umid_token(self) -> Optional[str]:
        logger.info("[PHONE] Recupero umidToken reale...")
        try:
            headers = {
                "accept":         "*/*",
                "accept-language":"en-US,en;q=0.9,it;q=0.8",
                "content-type":   "application/x-www-form-urlencoded; charset=UTF-8",
                "origin":         "https://www.aliexpress.com",
                "referer":        "https://www.aliexpress.com/",
                "user-agent":     UA,
            }
            response = await safe_get(
                self.session, UMID_URL, headers,
                timeout=15.0, params={"_bx-v": "2.5.36"},
            )
            if response.status_code == 200:
                data = response.json()
                tn   = data.get("tn")
                if tn:
                    logger.info(f"[PHONE] umidToken ottenuto: {tn[:30]}...")
                    return tn
        except Exception as e:
            logger.debug(f"[PHONE] Errore fetch umidToken: {e}")
        return None

    # ── identity.init ────────────────────────────────────────────────────────

    async def identity_init(self, login_name: str, login_name_type: str,
                            login_name_prefix: Optional[str] = None,
                            umid_token: Optional[str] = None,
                            tentativo: int = 1) -> dict:
        if tentativo > 3:
            return {"status": "Error", "message": "Tentativi esauriti"}

        if self._is_token_expired():
            if not await self._bootstrap_new_token():
                return {"status": "Error", "message": "Bootstrap token fallito"}

        if not umid_token:
            umid_token = await self._fetch_umid_token()
            if not umid_token:
                tele       = build_telemetry(int(time.time() * 1000), REFERER_LOGIN)
                umid_token = tele["umidToken"]

        identity_referer = self._build_identity_referer(
            login_name, login_name_type, login_name_prefix
        )
        bx_umid = (
            f"TOKEN3_INIT_CALLBACK_NOT_CALLED@@{identity_referer}"
            f"@@{int(time.time() * 1000)}"
        )

        data_payload = {
            "bx-umidToken":  bx_umid,
            "bizSegment":    "BUYER",
            "identityScene": "FIND_ACCOUNT",
            "loginNamePrefix": login_name_prefix,
            "loginNameType": login_name_type,
            "loginName":     login_name,
            "platform":      "pc",
            "showError":     True,
            "umidToken":     umid_token,
            "lang":          "it_IT",
        }

        now_ms    = int(time.time() * 1000)
        timestamp = str(now_ms)
        data_str  = json.dumps(data_payload, separators=(",", ":"))
        sign      = self._sign_login(timestamp, data_str)
        params    = self._login_params("mtop.global.user.identity.init", sign, timestamp)
        form_data = {"data": data_str}

        try:
            response = await safe_post(
                self.session, MTOP_IDENTITY_INIT_URL,
                params=params,
                headers=self._build_login_headers(),
                data=form_data,
            )
            status_code  = getattr(response, "status_code", None)
            if status_code != 200:
                return {"status": "Error", "message": f"HTTP {status_code}"}

            res_json     = response.json()
            ret_messages = res_json.get("ret", [])
            logger.info(f"MTOP ret [identity.init]: {ret_messages}")

            is_expired = any(
                "FAIL_SYS_TOKEN_EXPIRED" in m
                or "FAIL_SYS_ILLEGAL_ACCESS" in m
                or "FAIL_SYS_TOKEN_EMPTY" in m
                for m in ret_messages
            )
            if is_expired:
                logger.warning("[identity.init] Token scaduto, refresh e retry...")
                if await self._bootstrap_new_token():
                    return await self.identity_init(
                        login_name, login_name_type, login_name_prefix,
                        umid_token, tentativo + 1
                    )
                return {"status": "Error", "message": "Refresh token fallito"}

            if ret_matches(ret_messages, RET_NOT_FOUND_PATTERNS):
                logger.info("[identity.init] ret indica utente non esistente -> not_found")
                return {
                    "status":  "NotFound",
                    "message": ret_messages[0] if ret_messages else "user not existed",
                    "data":    res_json,
                }

            if ret_matches(ret_messages, RET_RATE_LIMIT_PATTERNS):
                logger.warning(f"[identity.init] rate limit: {ret_messages}")
                return {
                    "status":  "RateLimit",
                    "message": ret_messages[0] if ret_messages else "rate limit",
                    "data":    res_json,
                }

            if not any("SUCCESS" in m for m in ret_messages):
                return {
                    "status":  "Error",
                    "message": ret_messages[0] if ret_messages else "ret vuoto",
                    "data":    res_json,
                }

            self._save_state()
            return {"status": "SUCCESS", "data": res_json}

        except Exception as e:
            logger.exception("Errore richiesta identity.init")
            return {"status": "Error", "message": str(e)}

    # ── getUserByToken ────────────────────────────────────────────────────────

    async def get_user_by_token(self, biz_token: str,
                                umid_token: Optional[str] = None,
                                token_type: str = "VERIFICATION_TOKEN",
                                tentativo: int = 1) -> dict:
        if tentativo > 3:
            return {"status": "Error", "message": "Tentativi esauriti"}
        if not biz_token:
            return {"status": "Error", "message": "bizToken mancante"}
        if self._is_token_expired():
            if not await self._bootstrap_new_token():
                return {"status": "Error", "message": "Bootstrap token fallito"}

        if not umid_token:
            umid_token = await self._fetch_umid_token()
            if not umid_token:
                tele       = build_telemetry(int(time.time() * 1000), REFERER_LOGIN)
                umid_token = tele["umidToken"]

        data_payload = {
            "bx-umidToken":  umid_token,
            "bizSegment":    "BUYER",
            "identityScene": "FIND_ACCOUNT",
            "platform":      "pc",
            "bizToken":      biz_token,
            "tokenType":     token_type,
            "umidToken":     umid_token,
            "lang":          "it_IT",
        }

        now_ms    = int(time.time() * 1000)
        timestamp = str(now_ms)
        data_str  = json.dumps(data_payload, separators=(",", ":"))
        sign      = self._sign_login(timestamp, data_str)
        params    = self._login_params("mtop.global.user.getUserByToken", sign, timestamp)
        form_data = {"data": data_str}

        try:
            response = await safe_post(
                self.session, MTOP_GET_USER_BY_TOKEN_URL,
                params=params,
                headers=self._build_login_headers(),
                data=form_data,
            )
            status_code  = getattr(response, "status_code", None)
            if status_code != 200:
                return {"status": "Error", "message": f"HTTP {status_code}"}

            res_json     = response.json()
            ret_messages = res_json.get("ret", [])
            logger.info(f"MTOP ret [getUserByToken]: {ret_messages}")

            is_expired = any(
                "FAIL_SYS_TOKEN_EXPIRED" in m
                or "FAIL_SYS_ILLEGAL_ACCESS" in m
                or "FAIL_SYS_TOKEN_EMPTY" in m
                for m in ret_messages
            )
            if is_expired:
                logger.warning("[getUserByToken] Token scaduto, refresh e retry...")
                if await self._bootstrap_new_token():
                    return await self.get_user_by_token(
                        biz_token, umid_token, token_type, tentativo + 1
                    )
                return {"status": "Error", "message": "Refresh token fallito"}

            if ret_matches(ret_messages, RET_NOT_FOUND_PATTERNS):
                logger.info("[getUserByToken] ret indica utente non esistente")
                return {
                    "status":  "NotFound",
                    "message": ret_messages[0] if ret_messages else "user not existed",
                    "data":    res_json,
                }

            if ret_matches(ret_messages, RET_RATE_LIMIT_PATTERNS):
                logger.warning(f"[getUserByToken] rate limit: {ret_messages}")
                return {
                    "status":  "RateLimit",
                    "message": ret_messages[0] if ret_messages else "rate limit",
                    "data":    res_json,
                }

            if not any("SUCCESS" in m for m in ret_messages):
                return {
                    "status":  "Error",
                    "message": ret_messages[0] if ret_messages else "ret vuoto",
                    "data":    res_json,
                }

            self._save_state()
            return {"status": "SUCCESS", "data": res_json}

        except Exception as e:
            logger.exception("Errore richiesta getUserByToken")
            return {"status": "Error", "message": str(e)}

    # ── ensure_credentials ───────────────────────────────────────────────────

    async def ensure_credentials(self) -> dict:
        if not self.session.cookies.get("cna"):
            if not await self._bootstrap_cna():
                return {"ok": False, "regenerated": False, "message": "Cookie 'cna' mancante"}
        regenerated = False
        if self._is_token_expired():
            if not await self._bootstrap_new_token():
                return {"ok": False, "regenerated": False, "message": "Bootstrap token fallito"}
            regenerated = True
        self._save_state()
        return {"ok": True, "regenerated": regenerated}

    # ── _mtop_request ────────────────────────────────────────────────────────

    async def _mtop_request(self, mtop_url: str, api_name: str, data_payload: dict,
                            extra_params: dict = None, referer: str = REFERER_EMAIL,
                            tentativo: int = 1) -> dict:
        if tentativo > 3:
            return {"status": "Error", "message": "Tentativi esauriti"}

        if not self.session.cookies.get("cna"):
            if not await self._bootstrap_cna():
                return {"status": "Error", "message": "Cookie 'cna' mancante"}

        if self._is_token_expired():
            if not await self._bootstrap_new_token():
                return {"status": "Error", "message": "Bootstrap token fallito"}

        now_ms    = int(time.time() * 1000)
        tele      = build_telemetry(now_ms, referer)
        timestamp = str(now_ms)
        data_str  = json.dumps(data_payload, separators=(",", ":"))
        token     = self._get_token_from_cookies() or ""
        sign      = self._calcola_sign(token, timestamp, data_str)

        params = {
            "jsv":      "2.5.1",
            "appKey":   self.app_key,
            "t":        timestamp,
            "sign":     sign,
            "v":        "1.0",
            "type":     "originaljson",
            "api":      api_name,
            "dataType": "jsonp",
        }
        if extra_params:
            params.update(extra_params)

        form_data = {
            "data":         data_str,
            "bx-ua":        tele["bx-ua"],
            "bx-umidtoken": tele["bx-umidtoken"],
            "bx-sys":       "ua-l:no__um-l:no__js:https://g.alicdn.com/",
        }

        try:
            response = await safe_post(
                self.session, mtop_url,
                params=params,
                headers=self._build_common_headers(referer),
                data=form_data,
            )
            status_code  = getattr(response, "status_code", None)
            if status_code != 200:
                return {"status": "Error", "message": f"HTTP {status_code}"}

            res_json     = response.json()
            ret_messages = res_json.get("ret", [])
            logger.info(f"MTOP ret [{api_name}]: {ret_messages}")

            is_expired = any(
                "FAIL_SYS_TOKEN_EXPIRED" in m
                or "FAIL_SYS_ILLEGAL_ACCESS" in m
                or "FAIL_SYS_TOKEN_EMPTY" in m
                for m in ret_messages
            )
            if is_expired:
                logger.warning("Token scaduto, refresh e retry...")
                if await self._bootstrap_new_token():
                    return await self._mtop_request(
                        mtop_url, api_name, data_payload, extra_params,
                        referer, tentativo + 1
                    )
                return {"status": "Error", "message": "Refresh token fallito"}

            self._save_state()
            return {"status": "SUCCESS", "data": res_json}

        except Exception as e:
            logger.exception(f"Errore richiesta MTOP [{api_name}]")
            return {"status": "Error", "message": str(e)}

    # ── API pubbliche lookup ──────────────────────────────────────────────────

    async def esegui_richiesta_email(self, passport_id: str, tentativo: int = 1) -> dict:
        cna    = self.session.cookies.get("cna", "")
        now_ms = int(time.time() * 1000)
        tele   = build_telemetry(now_ms, REFERER_EMAIL)
        data_payload = {
            "ua":            tele["ua"],
            "umidToken":     tele["umidToken"],
            "cna":           cna,
            "lang":          "it_IT",
            "fuzzyPassport": False,
            "passport":      passport_id,
        }
        return await self._mtop_request(
            MTOP_EMAIL_URL,
            "mtop.aliexpress.member.member.center.findDesMemInfoList",
            data_payload,
            extra_params={"_bx-v": "2.5.36"},
            referer=REFERER_EMAIL,
            tentativo=tentativo,
        )

    async def esegui_richiesta_phone(self, phone_passport: str, tentativo: int = 1) -> dict:
        await self._visit_phone_page()
        await self._phone_suffix_init()
        umid_token = await self._fetch_umid_token()

        cna    = self.session.cookies.get("cna", "")
        now_ms = int(time.time() * 1000)
        tele   = build_telemetry(now_ms, REFERER_PHONE)

        data_payload = {
            "ua":            tele["ua"],
            "umidToken":     umid_token if umid_token else tele["umidToken"],
            "cna":           cna,
            "lang":          "it_IT",
            "fuzzyPassport": False,
            "passport":      phone_passport,
        }
        return await self._mtop_request(
            MTOP_EMAIL_URL,
            "mtop.aliexpress.member.member.center.findDesMemInfoList",
            data_payload,
            extra_params={"_bx-v": "2.5.36"},
            referer=REFERER_PHONE,
            tentativo=tentativo,
        )


# ===========================================================================
# Social/UGC profile  (fetch_social_profile)
# ===========================================================================

async def _bootstrap_social(client: httpx.AsyncClient, encoded_id: str = "") -> bool:
    """Bootstrap cookie + token per il profilo UGC star.aliexpress.com."""
    nav = {
        "user-agent":      UA,
        "accept":          "text/html,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "sec-fetch-dest":  "document",
        "sec-fetch-mode":  "navigate",
        "sec-fetch-site":  "none",
    }

    # 1. AliExpress homepage → cna
    if not _cookies_dict(client).get("cna"):
        try:
            await client.get("https://www.aliexpress.com/", headers=nav, timeout=15)
        except Exception:
            pass

    # 2. Star homepage
    try:
        await client.get(
            STAR_HOME,
            headers={**nav, "referer": "https://www.aliexpress.com/",
                     "sec-fetch-site": "cross-site"},
            timeout=15,
        )
    except Exception:
        pass

    # 3. Pagina profilo (se abbiamo encoded_id)
    if encoded_id:
        try:
            await client.get(
                f"{STAR_PROFILE_BASE}{encoded_id}?encode=1",
                headers={**nav, "referer": STAR_HOME, "sec-fetch-site": "same-origin"},
                timeout=15,
            )
        except Exception:
            pass

    # 4. Probe GET sull'API → AliExpress emette _m_h5_tk
    try:
        ts   = str(int(time.time() * 1000))
        data = json.dumps(
            {"toMemberSeq": encoded_id or "0", "channelId": "20", "encode": 1},
            separators=(",", ":"),
        )
        ref = f"{STAR_PROFILE_BASE}{encoded_id}?encode=1" if encoded_id else STAR_HOME
        await client.get(
            URL_BASE_INFO,
            params={
                "jsv": "2.5.1", "appKey": APP_KEY_SOCIAL,
                "t": ts, "sign": "", "v": "1.0",
                "api": API_BASE_INFO, "type": "jsonp",
                "dataType": "jsonp", "callback": "mtopjsonp1",
                "data": data,
            },
            headers={
                "user-agent":     UA,
                "referer":        ref,
                "accept":         "*/*",
                "sec-fetch-dest": "script",
                "sec-fetch-mode": "no-cors",
                "sec-fetch-site": "same-site",
            },
            timeout=10,
        )
    except Exception:
        pass

    token = _get_h5_token(client)
    logger.info(f"[BOOT-SOCIAL] token={'OK' if token else 'MISSING'}")
    return bool(token)


async def _call_base_info(client: httpx.AsyncClient,
                          member_id: str,
                          encode: int,
                          attempt: int = 1) -> dict:
    """
    Chiama mtop.aliexpress.ugc.feed.member.baseInfo.
    encode=0 → member_seq numerico
    encode=1 → encoded ID (base62)
    """
    if attempt > 3:
        return {"status": "Error", "message": "Tentativi esauriti"}

    if _token_expired_social(client):
        await _bootstrap_social(client, member_id if encode == 1 else "")

    token    = _get_h5_token(client)
    ts       = str(int(time.time() * 1000))
    payload  = {"toMemberSeq": str(member_id), "channelId": "20", "encode": encode}
    data_str = json.dumps(payload, separators=(",", ":"))
    sig      = _sign_social(token, ts, APP_KEY_SOCIAL, data_str)

    params = {
        "jsv":      "2.5.1",
        "appKey":   APP_KEY_SOCIAL,
        "t":        ts,
        "sign":     sig,
        "api":      API_BASE_INFO,
        "v":        "1.0",
        "type":     "jsonp",
        "dataType": "jsonp",
        "callback": "mtopjsonp1",
        "data":     data_str,
    }

    headers = {
        "accept":             "*/*",
        "accept-language":    "en-US,en;q=0.9,it;q=0.8",
        "referer":            STAR_HOME,
        "sec-ch-ua":          '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest":     "script",
        "sec-fetch-mode":     "no-cors",
        "sec-fetch-site":     "same-site",
        "user-agent":         UA,
    }

    try:
        r = await client.get(URL_BASE_INFO, params=params, headers=headers, timeout=20)
    except Exception as e:
        return {"status": "Error", "message": str(e)}

    if r.status_code != 200:
        return {"status": "Error", "message": f"HTTP {r.status_code}"}

    # Risposta JSONP: mtopjsonp1({...})
    text = r.text.strip()
    m    = re.match(r'^[^(]+\((.+)\)\s*;?\s*$', text, re.DOTALL)
    if not m:
        return {"status": "Error", "message": f"JSONP parse failed: {text[:100]}"}

    try:
        res = json.loads(m.group(1))
    except Exception as e:
        return {"status": "Error", "message": f"JSON decode: {e}"}

    ret = res.get("ret", [])
    logger.info(f"[API-SOCIAL] encode={encode} ret={ret}")

    # Token scaduto → refresh
    if any(x in msg for msg in ret for x in (
        "FAIL_SYS_TOKEN_EXPIRED", "FAIL_SYS_ILLEGAL_ACCESS", "FAIL_SYS_TOKEN_EMPTY"
    )):
        for k in ("_m_h5_tk", "_m_h5_tk_enc"):
            try:
                del client.cookies[k]
            except Exception:
                pass
        await _bootstrap_social(client, member_id if encode == 1 else "")
        return await _call_base_info(client, member_id, encode, attempt + 1)

    return {"status": "SUCCESS", "ret": ret, "res": res}


def _extract_encoded_id(data_inner: dict) -> Optional[str]:
    """Estrae l'encoded ID da profileShareUrl nella risposta baseInfo."""
    share_url = data_inner.get("profileShareUrl", "")
    if share_url:
        m = re.search(r'/backflow/([A-Za-z0-9_-]{8,25})', share_url)
        if m:
            candidate = m.group(1)
            if not candidate.isdigit():
                return candidate
    for val in data_inner.values():
        if isinstance(val, str):
            m = re.search(r'/backflow/([A-Za-z0-9_-]{8,25})', val)
            if m and not m.group(1).isdigit():
                return m.group(1)
    return None


def _parse_social_profile(data_inner: dict, encoded_id: str = "") -> dict:
    """Normalizza i campi del profilo UGC in una struttura piatta."""
    return {
        "exists":           True,
        "member_seq":       data_inner.get("memberSeq"),
        "nickname":         data_inner.get("nickName"),
        "contact_name":     data_inner.get("contactName"),
        "country":          data_inner.get("country"),
        "buyer_level":      data_inner.get("buyerLevel"),
        "big_avatar":       data_inner.get("bigAvatar"),
        "avatar":           data_inner.get("avatar"),
        "fans_count":       data_inner.get("fansCount", 0),
        "follow_count":     data_inner.get("followCount", 0),
        "post_count":       data_inner.get("postCount", 0),
        "like_count":       data_inner.get("likeCount", 0),
        "comment_count":    data_inner.get("commentCount", 0),
        "main_profile":     data_inner.get("mainProfile", False),
        "ban":              data_inner.get("ban", False),
        "seller":           data_inner.get("seller", False),
        "official_account": data_inner.get("officialAccount", False),
        "encoded_id":       encoded_id,
    }


async def fetch_social_profile(numeric_member_seq: str) -> dict:
    """
    Dato un member_seq numerico (es. "6485029612"):
      1. baseInfo encode=0  → profilo + profileShareUrl
      2. Estrai encoded_id da profileShareUrl
      3. baseInfo encode=1 + encoded_id → profilo completo arricchito
    Restituisce un dict con i campi del profilo o {"status": "Error/NOT FOUND", ...}.
    """
    async with httpx.AsyncClient(follow_redirects=True, headers={"user-agent": UA}) as client:

        await _bootstrap_social(client)

        # STEP 1: encode=0
        logger.info(f"[SOCIAL/STEP1] baseInfo encode=0 per member_seq={numeric_member_seq}")
        r1 = await _call_base_info(client, numeric_member_seq, encode=0)

        if r1.get("status") != "SUCCESS":
            return {
                "status":  "Error",
                "step":    1,
                "message": r1.get("message"),
                "ret":     r1.get("ret", []),
            }

        res1   = r1["res"]
        data1  = res1.get("data", {})
        inner1 = data1.get("data") if isinstance(data1.get("data"), dict) else data1

        if not inner1 or not inner1.get("nickName"):
            return {"status": "NOT FOUND", "step": 1, "ret": r1.get("ret", []), "raw": data1}

        # STEP 2: encoded_id
        encoded_id = _extract_encoded_id(inner1)
        logger.info(f"[SOCIAL/STEP2] encoded_id estratto: {encoded_id!r}")

        if not encoded_id:
            logger.warning("[SOCIAL/STEP2] profileShareUrl senza encoded ID, uso dati step 1")
            return _parse_social_profile(inner1, encoded_id="")

        # STEP 3: encode=1
        logger.info(f"[SOCIAL/STEP3] baseInfo encode=1 per encoded_id={encoded_id}")
        r2 = await _call_base_info(client, encoded_id, encode=1)

        if r2.get("status") != "SUCCESS":
            logger.warning(f"[SOCIAL/STEP3] encode=1 fallito: {r2.get('ret')} — uso step 1")
            return _parse_social_profile(inner1, encoded_id=encoded_id)

        res2   = r2["res"]
        data2  = res2.get("data", {})
        inner2 = data2.get("data") if isinstance(data2.get("data"), dict) else data2

        if not inner2 or not inner2.get("nickName"):
            return _parse_social_profile(inner1, encoded_id=encoded_id)

        return _parse_social_profile(inner2, encoded_id=encoded_id)


# ===========================================================================
# _run_check  (pipeline lookup → identity → getUserByToken → social)
# ===========================================================================

def _extract_user_id_from_result(formatted: dict) -> Optional[str]:
    """
    Estrae il userId (member_seq numerico) dalla struttura formatted prodotta da
    format_response(). Cerca in 'show' (campo 'id') e in 'full' (returnObject).
    """
    show = formatted.get("show") or {}

    # 1. Presente direttamente in show["id"] (arrivato da getUserByToken)
    if isinstance(show, dict):
        uid = show.get("id")
        if uid and str(uid).strip():
            return str(uid).strip()

    # 2. Cerca in full.returnObject[*].userId
    full       = formatted.get("full") or {}
    return_obj = full.get("returnObject") or []
    if isinstance(return_obj, list):
        for account in return_obj:
            if isinstance(account, dict):
                uid = account.get("userId") or account.get("loginId")
                if uid and str(uid).strip().isdigit():
                    return str(uid).strip()

    # 3. Cerca in full.user_by_token.data.userId
    ubt = full.get("user_by_token") or {}
    if isinstance(ubt, dict):
        d = ubt.get("data") or {}
        if isinstance(d.get("data"), dict):
            d = d["data"]
        uid = d.get("userId")
        if uid and str(uid).strip():
            return str(uid).strip()

    return None


async def _run_check(aliex: AliexpressClient, passport: str, lookup_type: str) -> dict:
    """
    Pipeline completa:
      1) findDesMemInfoList  → gate definitivo
      2) identity.init       → bizToken
      3) getUserByToken      → dati parziali (userId incluso)
      4) fetch_social_profile(userId) → profilo UGC completo
    """
    # ── STEP 1: gate ─────────────────────────────────────────────────────────
    if lookup_type == "email":
        fdml_raw = await aliex.esegui_richiesta_email(passport)
    else:
        phone_passport = parse_phone_value(passport)
        logger.info(f"[PHONE] passport normalizzato: {passport!r} -> {phone_passport!r}")
        fdml_raw = await aliex.esegui_richiesta_phone(phone_passport)

    if fdml_raw.get("status") == "Error":
        return {"service": DOMAIN, "result": "error", "msg": fdml_raw.get("message")}

    fdml_data_block = fdml_raw.get("data", {}) or {}
    fdml_inner      = extract_inner(fdml_data_block)

    early = interpret_inner(fdml_inner)
    if early:
        return early

    fdml_code = fdml_inner.get("code")
    fdml_ok   = (fdml_code == 0 and fdml_inner.get("success") is True)
    if not fdml_ok:
        return {"service": DOMAIN, "result": "not_found"}

    # ── STEP 2: identity.init ────────────────────────────────────────────────
    login_name, login_name_type, login_name_prefix = split_identity_input(passport, lookup_type)
    logger.info(
        f"[IDENTITY] input -> name={login_name!r} type={login_name_type} "
        f"prefix={login_name_prefix!r}"
    )

    umid_token = await aliex._fetch_umid_token()
    init_resp  = await aliex.identity_init(
        login_name=login_name,
        login_name_type=login_name_type,
        login_name_prefix=login_name_prefix,
        umid_token=umid_token,
    )

    init_status     = init_resp.get("status")
    init_data_block = init_resp.get("data", {}) or {}
    init_inner      = (
        init_data_block.get("data") or {}
        if isinstance(init_data_block, dict) else {}
    )
    info = interpret_identity_init(init_inner) or {}
    logger.info(f"[IDENTITY] init status={init_status} info={info}")

    biz_token = None
    if init_status == "SUCCESS" and info.get("exist"):
        biz_token = info.get("token")
    elif init_status == "NotFound":
        logger.info("[IDENTITY] init dice not-existed; ci fidiamo del gate")
    elif init_status == "RateLimit":
        logger.warning("[IDENTITY] rate limit: ritorno trovato senza parziali")
    elif init_status != "SUCCESS":
        logger.warning(f"[IDENTITY] init errore (degradato): {init_resp.get('message')}")

    # ── STEP 3: getUserByToken ───────────────────────────────────────────────
    ubt_data = None
    if biz_token:
        ubt = await aliex.get_user_by_token(biz_token, umid_token=umid_token)
        if ubt.get("status") == "SUCCESS":
            ubt_data = ubt.get("data")
        else:
            logger.info(
                f"[ENRICH] getUserByToken non SUCCESS ({ubt.get('status')}): "
                f"{ubt.get('message')}"
            )

    # ── STEP 4: profilo social/UGC ───────────────────────────────────────────
    # Serve l'userId: cercalo nei dati già raccolti prima di costruire formatted
    _pre_formatted = format_response(fdml_inner, user_by_token=ubt_data)
    user_id        = _extract_user_id_from_result(_pre_formatted)
    social_profile: Optional[dict] = None

    if user_id:
        logger.info(f"[SOCIAL] userId trovato ({user_id}), recupero profilo UGC...")
        try:
            social_raw = await fetch_social_profile(user_id)
            if isinstance(social_raw, dict) and social_raw.get("exists"):
                social_profile = social_raw
                logger.info(
                    f"[SOCIAL] profilo recuperato: nickname={social_raw.get('nickname')!r}, "
                    f"country={social_raw.get('country')!r}, "
                    f"fans={social_raw.get('fans_count')}"
                )
            else:
                logger.info(f"[SOCIAL] profilo non trovato o vuoto: {social_raw.get('status')}")
        except Exception as e:
            logger.warning(f"[SOCIAL] Errore recupero profilo: {e}")
    else:
        logger.info("[SOCIAL] userId non disponibile, skip profilo UGC")

    # ── Formattazione finale (con tutti i dati disponibili) ──────────────────
    formatted = format_response(
        fdml_inner,
        user_by_token=ubt_data,
        identity_init_block=init_data_block if init_data_block else None,
        social_profile=social_profile,
    )



    # ── Output finale: solo service, result, return ──────────────────────────
    return {"service": DOMAIN, "result": "found", "return": formatted}


# ===========================================================================
# fetch_once / fetch  (entry point pubblico)
# ===========================================================================

async def _fetch_once(passport: str, lookup_type: str) -> dict:
    """Singola sessione completa: bootstrap + _run_check."""
    async with new_http_client() as client:
        aliex = AliexpressClient(client)
        creds = await aliex.ensure_credentials()
        if not creds.get("ok"):
            return {
                "service": DOMAIN,
                "result":  "error",
                "msg":     creds.get("message", "Preparazione credenziali fallita"),
            }
        regenerated = creds.get("regenerated", False)

        if not regenerated:
            return await _run_check(aliex, passport, lookup_type)

        logger.info("[FASE 2] Token rigenerati: nuovo client, reimporto e check...")
        async with new_http_client() as client2:
            aliex2 = AliexpressClient(client2)
            return await _run_check(aliex2, passport, lookup_type)


async def fetch(value: str, lookup_type: str, alert_module: bool = False) -> dict:
    """
    Entry point pubblico.

    Args:
        value:       email o numero di telefono (con prefisso internazionale).
        lookup_type: 'email' oppure 'phone'.
        alert_module: riservato per integrazioni future.

    Returns:
        {
          "service": "aliexpress.com",
          "result":  "found" | "not_found" | "error" | "rate_limit",
          "return":  {                      # presente solo se result == "found"
            "show": {                       # dati sintetici, pronti all'uso
              "id":            ...,         # userId numerico
              "name":          ...,         # contact_name dal social, altrimenti nickName
              "email":         ...,         # email in chiaro (se disponibile)
              "avatar":        ...,         # URL avatar
              "partial_email": ...,         # email mascherata da getUserByToken
              "login_id":      ...,         # loginId account
              "phone":         ...,         # telefono parziale (se disponibile)
              "username":      ...,         # nickname dal profilo social/UGC
              "exists":        True,
              "page_type":     ...          # es. "EMAIL_CODE"
            },
            "full": {                       # dati grezzi completi
              "returnObject":  [...],       # lista account da findDesMemInfoList
              "identity":      {...},       # risposta grezza identity.init
              "user_by_token": {...},       # risposta grezza getUserByToken
              "socialProfile": {...}        # profilo UGC completo (se disponibile)
            }
          }
        }
    """
    if lookup_type not in TARGET_TYPES:
        return {
            "service": DOMAIN,
            "result":  "error",
            "msg":     f"lookup_type '{lookup_type}' non supportato",
        }

    passport = value.strip()


    result = await _fetch_once(passport, lookup_type)

    # Retry su rate_limit
    MAX_RATE_LIMIT_RETRIES = 2
    retry_count = 0

    while result.get("result") == "rate_limit" and retry_count < MAX_RATE_LIMIT_RETRIES:
        retry_count += 1
        logger.warning(
            f"[RATE_LIMIT] Rilevato — reset e retry {retry_count}/{MAX_RATE_LIMIT_RETRIES}..."
        )
        reset_token_file(TOKEN_FILE)
        result = await _fetch_once(passport, lookup_type)

    if result.get("result") == "rate_limit" and retry_count >= MAX_RATE_LIMIT_RETRIES:
        logger.warning("[RATE_LIMIT] Tentativi esauriti.")

    return result


# ===========================================================================
# __main__
# ===========================================================================

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    import asyncio
    _res = asyncio.run(fetch(_sys.argv[1].strip(), "email"))
    print(json.dumps(_res, indent=4, ensure_ascii=False))
