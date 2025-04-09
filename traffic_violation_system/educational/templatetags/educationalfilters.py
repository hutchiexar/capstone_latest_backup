import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def contains_pdf(value):
    """Check if content contains PDF page images or PDF image references"""
    if not value:
        return False
    
    # Check for various PDF indicators
    return ('<div class="pdf-page-image">' in value or 
            'PDF extracted image' in value or
            'data-pdf-content="true"' in value)

@register.filter
def extract_first_pdf_image(html_content):
    """Extract the first PDF image from content and wrap it properly"""
    if not html_content:
        return ""
    
    # First, look for direct PDF extracted image references
    # This matches the format seen in the screenshot: "PDF extracted image 1"
    pdf_img_pattern = r'<img[^>]*src="([^"]*PDF extracted image 1[^"]*)"[^>]*>'
    pdf_img_matches = re.findall(pdf_img_pattern, html_content, re.IGNORECASE)
    
    if pdf_img_matches:
        return mark_safe(f'<img src="{pdf_img_matches[0]}" alt="PDF Preview" class="img-fluid">')
    
    # Alternative approach - find all img tags and look for one with PDF in the src/alt
    img_pattern = r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>'
    img_matches = re.findall(img_pattern, html_content)
    
    for src, alt in img_matches:
        if 'PDF' in src or 'PDF' in alt or 'pdf' in src or 'extracted' in src.lower():
            return mark_safe(f'<img src="{src}" alt="{alt}" class="img-fluid">')
    
    # If no matches yet, try a simpler pattern to find any image
    simple_img_pattern = r'<img[^>]*src="([^"]*)"[^>]*>'
    simple_matches = re.findall(simple_img_pattern, html_content)
    
    if simple_matches and len(simple_matches) > 0:
        return mark_safe(f'<img src="{simple_matches[0]}" alt="PDF Preview" class="img-fluid">')
    
    # Last resort: just create a fixed placeholder for PDF preview
    return mark_safe('<div class="pdf-placeholder">PDF Document Preview</div>')

@register.filter
def is_pdf_topic(topic_content):
    """Determines if a topic contains PDF content based on various indicators"""
    if not topic_content:
        return False
    
    # Check for PDF specific strings in the content
    pdf_indicators = [
        'PDF extracted image',
        '<div class="pdf-page-image">',
        'data-content-type="pdf"',
        'application/pdf',
        '.pdf'
    ]
    
    for indicator in pdf_indicators:
        if indicator in topic_content:
            return True
    
    return False 