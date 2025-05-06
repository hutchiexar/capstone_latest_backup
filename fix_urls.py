import re

# Read the file
with open('traffic_violation_system/urls.py', 'r') as f:
    content = f.read()

# Add import for adjudication_history_views if not already present
if 'from . import adjudication_history_views' not in content:
    content = content.replace(
        'from . import adjudication_views',
        'from . import adjudication_views\nfrom . import adjudication_history_views'
    )

# Find the location to insert the adjudication history URL patterns
# Look for the last URL pattern before the closing bracket
pattern = r"(path\('violation/<int:violation_id>/adjudication-details/', adjudication_views\.get_adjudication_details, name='get_adjudication_details'\),\s*)\]\s*\+\s*static"


if re.search(pattern, content):
    # Insert the adjudication history URL patterns
    replacement = r"\1\n\n    # Adjudication History URLs\n    path('adjudication-history/', adjudication_history_views.adjudication_history, name='adjudication_history'),\n    path('adjudication-history/<int:violation_id>/', adjudication_history_views.adjudication_detail, name='adjudication_detail'),\n    path('adjudication-history/export/', adjudication_history_views.export_adjudication_history, name='export_adjudication_history'),\n] + static"
    
    content = re.sub(pattern, replacement, content)

# Write the updated content back to the file
with open('traffic_violation_system/urls.py', 'w') as f:
    f.write(content)

print("URLs file updated successfully.") 