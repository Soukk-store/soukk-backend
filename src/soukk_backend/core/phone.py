import re

# Lebanese mobile: +961 then 3 + 6 digits, or 70/71/76/78/79/81 + 6 digits
PHONE_PATTERN = re.compile(r"^\+961(3|70|71|76|78|79|81)\d{6}$")


def normalize_lebanese_phone(value: str) -> str:
    phone = value.replace(" ", "").replace("-", "")
    if not phone.startswith("+961"):
        phone = "+961" + phone.removeprefix("0")
    if not PHONE_PATTERN.match(phone):
        raise ValueError("Phone number must be a Lebanese mobile number, e.g. +961 XX XXX XXX")
    return phone
