#!/usr/bin/env python

# Script to fix the operator_application_review function

import re

# Path to the file
file_path = 'traffic_violation_system/views.py'

# Read the file
with open(file_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Find the operator_application_review function
pattern = r"def operator_application_review\(request, application_id\):.*?(?=@login_required|\Z)"
matches = re.findall(pattern, content, re.DOTALL)

if not matches:
    print("Could not find operator_application_review function")
    exit(1)

# Get the function content
func_content = matches[0]

# Find the get_or_create part
get_or_create_pattern = r"operator, created = Operator\.objects\.get_or_create\(.*?'new_pd_number': '',.*?'old_pd_number': '',.*?\)"
get_or_create_match = re.search(get_or_create_pattern, func_content, re.DOTALL)

if not get_or_create_match:
    print("Could not find the get_or_create part with empty PD numbers")
    exit(1)

# Original code block that needs to be replaced
original_code = get_or_create_match.group(0)

# New code block with unique PD number generation
new_code = """                    # Get user profile for address and other details
                    user_profile = application.user.userprofile
                    
                    # Generate a unique PD number
                    highest_pd = 0
                    try:
                        # Get all PD numbers, filtering out non-numeric ones
                        pd_numbers = Operator.objects.filter(
                            new_pd_number__iregex=r'^\d+$'
                        ).values_list('new_pd_number', flat=True)
                        
                        # Convert to integers for proper sorting
                        numeric_pds = [int(pd) for pd in pd_numbers if pd and pd.isdigit()]
                        
                        if numeric_pds:
                            highest_pd = max(numeric_pds)
                    except Exception as e:
                        # If there's any error, log it but continue with default numbering
                        print(f"Error determining highest PD number: {str(e)}")
                    
                    # Set the new PD number as next in sequence (XXX format)
                    new_pd_number = str(highest_pd + 1).zfill(3)
                    old_pd_number = f"OLD-{new_pd_number}"
                    
                    # Create or update operator record with safe attribute access
                    operator, created = Operator.objects.get_or_create(
                        user=application.user,
                        defaults={
                            'first_name': application.user.first_name,
                            'last_name': application.user.last_name,
                            'address': user_profile.address,
                            'new_pd_number': new_pd_number,
                            'old_pd_number': old_pd_number,
                        }
                    )"""

# Replace the code in the function
updated_func_content = func_content.replace(original_code, new_code)

# Replace the original function in the content
updated_content = content.replace(func_content, updated_func_content)

# Write the updated content back to the file
with open(file_path, 'w', encoding='utf-8') as file:
    file.write(updated_content)

print("Successfully updated operator_application_review function to generate unique PD numbers") 