#!/usr/bin/env python

# Script to replace 'is_active=True' with 'active=True' in views.py

with open('traffic_violation_system/views.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Count occurrences before replacement
count_before = content.count('is_active=True')
print(f"Found {count_before} occurrences of 'is_active=True'")

# Replace all occurrences
content_new = content.replace('is_active=True', 'active=True')

# Count occurrences after replacement
count_after = content_new.count('is_active=True')
print(f"After replacement: {count_after} occurrences of 'is_active=True'")
print(f"Replaced {count_before - count_after} occurrences")

if count_before > count_after:
    # Write changes back to the file
    with open('traffic_violation_system/views.py', 'w', encoding='utf-8') as file:
        file.write(content_new)
    print("Changes written to file")
else:
    print("No changes made to the file") 