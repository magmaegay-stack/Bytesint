import json
import os
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")


def phonenumbers_info_lookup(phone: str) -> dict:
    """Offline phone number validation and metadata using libphonenumber."""
    clean = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    result = {
        "target": clean,
        "service": "phonenumbers_info",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "result": "not_found",
        "return": {},
    }

    try:
        import phonenumbers
        from phonenumbers import geocoder, carrier, timezone as ph_timezone

        pn = phonenumbers.parse(clean, None)

        return_data = {"phone": clean}

        return_data["valid"] = phonenumbers.is_valid_number(pn)
        return_data["possible"] = phonenumbers.is_possible_number(pn)

        if not return_data["valid"]:
            result["result"] = "not_found"
            result["return"] = return_data
            return result

        nt = phonenumbers.number_type(pn)
        type_map = {
            phonenumbers.PhoneNumberType.MOBILE: "mobile",
            phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
            phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
            phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
            phonenumbers.PhoneNumberType.VOIP: "voip",
            phonenumbers.PhoneNumberType.PAGER: "pager",
            phonenumbers.PhoneNumberType.SHARED_COST: "shared_cost",
            phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "personal",
            phonenumbers.PhoneNumberType.UAN: "uan",
            phonenumbers.PhoneNumberType.VOICEMAIL: "voicemail",
        }
        return_data["line_type"] = type_map.get(nt, "unknown")

        region = phonenumbers.region_code_for_number(pn)
        if region:
            return_data["country_code"] = region

        location = geocoder.description_for_number(pn, "en")
        if location:
            return_data["location"] = location

        carrier_name = carrier.name_for_number(pn, "en")
        if carrier_name:
            return_data["carrier"] = carrier_name

        timezones = ph_timezone.time_zones_for_number(pn)
        if timezones:
            return_data["timezones"] = list(timezones)

        return_data["country_calling_code"] = pn.country_code
        return_data["national_number"] = str(pn.national_number)
        return_data["national_format"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.NATIONAL)
        return_data["international_format"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        return_data["e164_format"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)
        return_data["rfc3966_format"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.RFC3966)

        result["result"] = "found"
        result["return"] = {k: v for k, v in return_data.items() if v is not None}

    except Exception as e:
        result["result"] = "error"
        result["msg"] = str(e)

    return result


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = phonenumbers_info_lookup(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
