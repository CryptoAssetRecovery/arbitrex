# dashboard/templatetags/stat_filters.py

from django import template

register = template.Library()

@register.filter
def format_percentage(value):
    if value == "":
        return ""
    if value is None:
        return ""
    return f"{value:.2f}%"

@register.filter
def format_number(value):
    if value == "":
        return ""
    if value is None:
        return ""
    return f"{float(value):.3f}"
