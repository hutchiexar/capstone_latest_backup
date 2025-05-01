#!/usr/bin/env python3
"""
Script to add the missing validate_driver_data function to the views.py file
"""
import re
import os
import sys

def main():
    views_path = 'traffic_violation_system/views.py'
    backup_path = 'traffic_violation_system/views.py.bak_validate'
    
    # First, create a backup
    print(f"Creating backup at {backup_path}")
    try:
        with open(views_path, 'r', encoding='utf-8') as f:
            contents = f.read()
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(contents)
    except Exception as e:
        print(f"Error creating backup: {e}")
        return 1
    
    # Add the validation function before the clean_value function
    clean_value_pattern = r'def clean_value\(value\):'
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

def clean_value(value):\n"""
    
    # Check if the validation function already exists
    if 'def validate_driver_data(' in contents:
        print("Function validate_driver_data already exists. No changes needed.")
        return 0
    
    # Add the validation function before clean_value
    modified_contents = contents.replace(clean_value_pattern, validation_function + clean_value_pattern)
    
    # Write the modified file
    try:
        with open(views_path, 'w', encoding='utf-8') as f:
            f.write(modified_contents)
        print(f"Successfully added validate_driver_data function to {views_path}")
        return 0
    except Exception as e:
        print(f"Error writing file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 