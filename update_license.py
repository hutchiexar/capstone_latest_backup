#!/usr/bin/env python3

import re

# Read the file
with open('traffic_violation_system/views.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Define patterns to replace
pattern = r'if not license_number:[\s\n]+license_number = f"TEMP-{timezone\.now\(\)\.strftime\(\'%Y%m%d%H%M%S\'\)}"[\s\n]+logger\.info\(f"Generated temporary license number: {license_number}"\)'

# Replace with 'none'
replacement = 'if not license_number:\n                    license_number = "none"'

# Perform the replacement
modified_content = re.sub(pattern, replacement, content)

# Write the modified content back to the file
with open('traffic_violation_system/views.py', 'w', encoding='utf-8') as file:
    file.write(modified_content)

print("File updated successfully.") 