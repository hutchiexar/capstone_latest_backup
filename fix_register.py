import os
import re

# Path to the views.py file
views_file = 'traffic_violation_system/views.py'

# Read the file
with open(views_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Count occurrences of license check pattern
license_checks = re.findall(r"if UserProfile\.objects\.filter\(license_number=license_number\)\.exists\(\):", content)
print(f"Found {len(license_checks)} occurrences of license number check pattern")

# Directly update all instances
modified_content = content.replace(
    "if UserProfile.objects.filter(license_number=license_number).exists():",
    "if license_number and UserProfile.objects.filter(license_number=license_number).exists():"
)

# Check if modification was made
if content != modified_content:
    # Backup the original file
    backup_file = views_file + '.bak_license'
    if not os.path.exists(backup_file):
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Backup created at {backup_file}")
    
    # Write the modified content
    with open(views_file, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    print("License number check fixed! The register function now only checks for duplicates if the license number is not empty.")
else:
    print("No changes made.") 