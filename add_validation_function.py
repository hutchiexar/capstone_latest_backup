#!/usr/bin/env python3
"""
Script to add the missing validate_driver_data function to views.py
"""
import os
import sys

def main():
    views_path = 'traffic_violation_system/views.py'
    backup_path = 'traffic_violation_system/views.py.bak'
    
    # Create a backup
    print(f"Creating backup at {backup_path}")
    try:
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Error creating backup: {e}")
        return 1
    
    # Find the position to insert the validation function
    search_pattern = "def clean_value(value):"
    insert_position = content.find(search_pattern)
    
    if insert_position == -1:
        print("Could not find the clean_value function")
        return 1
    
    # Get the content before and after the insertion point
    content_before = content[:insert_position]
    content_after = content[insert_position:]
    
    # Create the validation function
    validation_function = """def validate_driver_data(data):
    \"\"\"
    Validate driver data before creating or updating a record
    Returns a tuple of (is_valid, error_message)
    \"\"\"
    errors = []
    
    # Required fields
    if not data.get('last_name'):
        errors.append("Last name is required")
    if not data.get('first_name'):
        errors.append("First name is required")
    if not data.get('address'):
        errors.append("Address is required")
    
    # Field length validations
    if data.get('last_name') and len(data['last_name']) > 100:
        errors.append(f"Last name too long (max 100 characters)")
    if data.get('first_name') and len(data['first_name']) > 100:
        errors.append(f"First name too long (max 100 characters)")
    if data.get('middle_initial') and len(data['middle_initial']) > 10:
        errors.append(f"Middle initial too long (max 10 characters)")
    if data.get('license_number') and len(data['license_number']) > 50:
        errors.append(f"License number too long (max 50 characters)")
    if data.get('contact_number') and len(data['contact_number']) > 20:
        errors.append(f"Contact number too long (max 20 characters)")
    if data.get('new_pd_number') and len(data['new_pd_number']) > 20:
        errors.append(f"New PD number too long (max 20 characters)")
    if data.get('old_pd_number') and len(data['old_pd_number']) > 20:
        errors.append(f"Old PD number too long (max 20 characters)")
    
    # Return validation result
    if errors:
        return False, ", ".join(errors)
    return True, ""


"""
    
    # Combine all parts
    new_content = content_before + validation_function + content_after
    
    # Write the modified content back to the file
    try:
        with open(views_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully added validate_driver_data function")
        return 0
    except Exception as e:
        print(f"Error writing file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 