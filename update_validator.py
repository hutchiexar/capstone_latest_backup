#!/usr/bin/env python3
"""
Script to update validate_driver_data function to accept "None" as a valid address
"""
import os
import sys
import re

def main():
    views_path = 'traffic_violation_system/views.py'
    backup_path = 'traffic_violation_system/views.py.bak_validator'
    
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
    
    # Pattern to find the address validation in validate_driver_data
    pattern = r"(if not data\.get\('address'\):)"
    
    # New check that accepts 'None' as valid
    replacement = r"if not data.get('address') and data.get('address') != 'None':  # Allow 'None' string as valid address"
    
    # Make the replacement
    modified_content = re.sub(pattern, replacement, content)
    
    if modified_content == content:
        print("No changes made - pattern not found")
        return 1
    
    # Write the modified content back to the file
    try:
        with open(views_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        print("Successfully updated validate_driver_data function to accept 'None' as valid address")
        return 0
    except Exception as e:
        print(f"Error writing file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 