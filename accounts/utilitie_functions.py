import re
from datetime import datetime
from decimal import Decimal

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_TYPE_MAPPING = {
    "image": {
        "types": ["image/png", "image/jpeg", "image/jpg", "image/webp"],
        "icon_class": "bi-file-earmark-image text-info",
    },
    "pdf": {
        "types": ["application/pdf"],
        "icon_class": "bi-file-earmark-pdf text-danger",
    },
    "text": {
        "types": ["text/plain", "text/csv", "text/html", "application/json"],
        "icon_class": "bi bi-file-text text-muted",
    },
    "zip": {
        "types": [
            "application/zip",
            "application/x-zip-compressed",
            "application/x-rar-compressed",
            "application/vnd.rar",
        ],
        "icon_class": "bi-file-zip text-secondary",
    },
    "word": {
        "types": [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.oasis.opendocument.text",
        ],
        "icon_class": "bi-file-earmark-word text-primary",
    },
    "spreadsheet": {
        "types": [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.oasis.opendocument.spreadsheet",
        ],
        "icon_class": "bi-file-spreadsheet text-success",
    },
    "presentation": {
        "types": [
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.oasis.opendocument.presentation",
        ],
        "icon_class": "bi-file-earmark-slides text-warning",
    },
    "epub": {
        "types": ["application/epub+zip"],
        "icon_class": "bi-book-half text-info",
    },
}

ALLOWED_CONTENT_TYPES = [
    item for types in FILE_TYPE_MAPPING.values() for item in types["types"]
]


def fetch_file_icon(content_type: str):
    """
    fetch icon class from content type
    """

    for file_type, details in FILE_TYPE_MAPPING.items():
        if content_type in details["types"]:
            return file_type, details["icon_class"]
    return "Unknown", "bi-file-earmark text-muted"


def date_convert(
    date_text: str,
    date_input_format: str = "%Y-%m-%d",
    date_output_format: str = "%d%b%y",
):
    """
    change date format

    Args:
        date_text (str): _description_
        date_input_format (str, optional): _description_. Defaults to "%Y-%m-%d".
        date_output_format (str, optional): output. Defaults to "%d%b%y".

    Returns:
        str: date
    """
    return (
        datetime.strptime(date_text, date_input_format)
        .strftime(date_output_format)
        .upper()
    )


def mask_email(value: str):
    """mask the email

    Args:
        value (str): email address

    Returns:
        str: masked email
    """

    local, domain = value.split("@", 1)
    return f"{local[:2]}******{local[-1:]}@{domain}"


def format_amount(amount: float):
    """Convert big values to readable format

    Args:
        amount (float): _description_

    Returns:
        _type_: str
    """
    if amount >= 1_00_00_000:
        return f"{amount / 1_00_00_000:.2f} Cr"
    elif amount >= 1_00_000:
        return f"{amount / 1_00_000:.2f} L"
    elif amount >= 1_000:
        return f"{amount / 1_000:.2f} K"
    else:
        return f"{amount:.2f}"


def convert_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def validate_password(password):
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    return bool(re.match(pattern, password))


def validate_uploaded_file(f):
    """Return (is_ok: bool, error_message: str or None)"""
    if not f:
        return False, "No file provided."
    if f.size > MAX_UPLOAD_SIZE:
        return False, f"File too large. Max {MAX_UPLOAD_SIZE // (1024*1024)} MB."
    ct = getattr(f, "content_type", "")
    if ct not in ALLOWED_CONTENT_TYPES:
        return False, "File type not allowed."
    return True, None


def calculate_size(size):
    units = ["bytes", "KB", "MB", "GB", "TB"]
    idx = 0
    size = float(size)

    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1

    return f"{size:.2f} {units[idx]}"
