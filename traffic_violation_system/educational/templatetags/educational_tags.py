from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using the key.
    Usage: {{ dictionary|get_item:key_variable }}
    """
    if not dictionary:
        return None
    
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None

@register.filter
def correct_count(responses):
    """
    Count the number of correct responses in a dictionary.
    Usage: {{ responses|correct_count }}
    """
    if not responses:
        return 0
    
    return sum(1 for response in responses.values() if response.is_correct)

@register.filter
def subtract(value, arg):
    """
    Subtract arg from value.
    Usage: {{ value|subtract:arg }}
    """
    try:
        return value - arg
    except (ValueError, TypeError):
        return value 