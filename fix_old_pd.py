#!/usr/bin/env python
"""
This script modifies the code that sets old_pd_number to leave it blank 
instead of setting it to "OLD-{new_pd_number}"
"""

import re

# Fix in operator_views.py
with open('traffic_violation_system/operator_views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the old_pd_number assignment
content = re.sub(
    r'operator\.old_pd_number = f"OLD-{new_pd_number}"',
    'operator.old_pd_number = ""  # Leave old PD number blank as requested',
    content
)

# Write the modified content back to the file
with open('traffic_violation_system/operator_views.py', 'w', encoding='utf-8') as f:
    f.write(content)
    
print("Updated operator_views.py")

# Fix in views.py
with open('traffic_violation_system/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the old_pd_number assignment
content = re.sub(
    r'old_pd_number = f"OLD-{new_pd_number}"',
    'old_pd_number = ""  # Leave old PD number blank as requested',
    content
)

# Write the modified content back to the file
with open('traffic_violation_system/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
    
print("Updated views.py")
print("Both files have been updated to leave old PD number blank") 