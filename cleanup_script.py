#!/usr/bin/env python3
"""
Script to remove the duplicate clean_value function in views.py
"""
import re
import sys

def main():
    views_path = 'traffic_violation_system/views.py'
    backup_path = 'traffic_violation_system/views.py.bak3'
    
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
    
    # Find the first occurrence of the clean_value function
    clean_value_pattern = r'def clean_value\(value\):[\s\S]+?return value\n\n'
    
    # Find all matches of the clean_value function
    matches = re.findall(clean_value_pattern, contents)
    
    if len(matches) > 1:
        print(f"Found {len(matches)} occurrences of clean_value function")
        
        # Replace the contents with just one occurrence of the function
        modified_contents = re.sub(clean_value_pattern, '', contents, count=1)
        
        # Write the modified contents back
        try:
            with open(views_path, 'w', encoding='utf-8') as f:
                f.write(modified_contents)
            print(f"Successfully removed duplicate clean_value function")
            return 0
        except Exception as e:
            print(f"Error writing modified file: {e}")
            return 1
    else:
        print("No duplicate clean_value function found")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 