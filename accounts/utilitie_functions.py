from datetime import datetime
from decimal import Decimal


def date_convert(date_text:str,date_input_format:str = "%Y-%m-%d",date_output_format:str = "%d%b%y"):
    """change date format 

    Args:
        date_text (str): _description_
        date_input_format (str, optional): _description_. Defaults to "%Y-%m-%d".
        date_output_format (str, optional): output. Defaults to "%d%b%y".

    Returns:
        str: date
    """
    return datetime.strptime(date_text,date_input_format).strftime(date_output_format).upper()

def mask_email(value:str):
    """mask the email

    Args:
        value (str): email address

    Returns:
        str: masked email
    """
    
    local, domain = value.split("@", 1)
    return f"{local[:2]}******{local[-1:]}@{domain}"

def format_amount(amount:float):
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