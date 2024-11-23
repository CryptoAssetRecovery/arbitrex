# utils.py
import black
from django.utils.html import escape
from django import template

register = template.Library()

@register.filter
def format_python_code(code: str) -> str:
    """
    Formats Python code using Black and escapes HTML characters.

    Args:
        code (str): The raw Python code.

    Returns:
        str: The formatted and escaped Python code.
    """
    try:
        formatted_code = black.format_str(code, mode=black.Mode())
    except black.NothingChanged:
        formatted_code = code
    except Exception as e:
        # Handle or log the exception as needed
        formatted_code = code  # Fallback to raw code

    return escape(formatted_code)