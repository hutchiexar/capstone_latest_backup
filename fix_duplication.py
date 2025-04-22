#!/usr/bin/env python

# Script to fix the duplication in operator_application_review

file_path = 'traffic_violation_system/views.py'

# Read the file
with open(file_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Find and fix the duplication
duplicate_text = """                                        # Get user profile for address and other details
                    user_profile = application.user.userprofile
                    
                    # Create or update operator record with safe attribute access
                                        # Get user profile for address and other details
                    user_profile = application.user.userprofile"""

fixed_text = """                                        # Get user profile for address and other details
                    user_profile = application.user.userprofile"""

# Replace the duplicated text
updated_content = content.replace(duplicate_text, fixed_text)

# Write the updated content back to the file
with open(file_path, 'w', encoding='utf-8') as file:
    file.write(updated_content)

print("Successfully fixed duplication in operator_application_review function") 