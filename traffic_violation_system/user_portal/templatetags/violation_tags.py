from django import template

register = template.Library()

@register.filter
def is_ncap(violation):
    """
    Check if a violation is an NCAP violation by looking at image fields
    Returns True if any of the image fields are not None/empty
    """
    return bool(violation.image or violation.driver_photo or 
                violation.vehicle_photo or violation.secondary_photo) 