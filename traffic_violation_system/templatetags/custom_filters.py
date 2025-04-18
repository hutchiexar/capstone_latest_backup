from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using key
    Usage: {{ my_dict|get_item:'key' }}
    """
    if key in dictionary:
        return dictionary[key]
    return None

@register.filter
def mul(value, arg):
    """
    Multiply the value by the argument
    Usage: {{ value|mul:5 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def floordiv(value, arg):
    """
    Perform integer division (floor division)
    Usage: {{ value|floordiv:5 }}
    """
    try:
        return int(float(value) // float(arg))
    except (ValueError, TypeError, ZeroDivisionError):
        return 0 