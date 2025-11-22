import re
from datetime import datetime
from decimal import Decimal

# Validation constants (same as before, adjust as needed)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    # Images
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    # PDF
    "application/pdf",
    # Text formats
    "text/plain",
    "text/csv",
    "text/html",
    "application/json",
    # Zip / compressed archives
    "application/zip",
    "application/x-zip-compressed",
    "application/x-rar-compressed",
    "application/vnd.rar",
    # Word documents
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    # Excel sheets
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    # PowerPoint
    "application/vnd.ms-powerpoint",  # .ppt
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    # OpenOffice / LibreOffice
    "application/vnd.oasis.opendocument.text",  # .odt
    "application/vnd.oasis.opendocument.spreadsheet",  # .ods
    "application/vnd.oasis.opendocument.presentation",  # .odp
    # Epub
    "application/epub+zip",
}


def date_convert(
    date_text: str,
    date_input_format: str = "%Y-%m-%d",
    date_output_format: str = "%d%b%y",
):
    """change date format

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
    if ALLOWED_CONTENT_TYPES and ct not in ALLOWED_CONTENT_TYPES:
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
