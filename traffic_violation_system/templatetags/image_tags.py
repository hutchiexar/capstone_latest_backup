import os
import base64
from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def get_image_as_base64(image_field):
    """
    Convert an image field to a base64 data URL for direct embedding in HTML.
    Usage: {% get_image_as_base64 user.userprofile.avatar %}
    """
    if not image_field:
        return ""
    
    try:
        # Get the file path
        if hasattr(image_field, 'path'):
            file_path = image_field.path
            
            # Check if file exists
            if not os.path.exists(file_path):
                return ""
            
            # Get the file extension
            _, file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()
            
            # Map extension to MIME type
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml'
            }
            mime_type = mime_types.get(file_extension, 'image/jpeg')
            
            # Read the file and encode it
            with open(file_path, 'rb') as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Return as data URL
            return f"data:{mime_type};base64,{encoded_string}"
        
    except Exception as e:
        # On any error, return empty string
        print(f"Error encoding image: {str(e)}")
        return ""
    
    return "" 