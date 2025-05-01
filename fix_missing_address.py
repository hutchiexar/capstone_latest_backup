#!/usr/bin/env python3
"""
Script to modify driver_import function to add "None" as a string value when address is missing
"""
import os
import sys
import re

def main():
    views_path = 'traffic_violation_system/views.py'
    backup_path = 'traffic_violation_system/views.py.bak_address'
    
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
    
    # Find the section that processes the address in the driver_import function
    address_pattern = r"(address = clean_value\(row\.get\(col_address, ''\)\) if col_address else None\s+if address:\s+address = str\(address\)\.strip\(\))"
    
    # New code to add "None" as default for missing addresses
    replacement = r"""address = clean_value(row.get(col_address, '')) if col_address else None
                        if address:
                            address = str(address).strip()
                        else:
                            address = "None"  # Set missing address to string "None" instead of null"""
    
    # Make the replacement
    modified_content = re.sub(address_pattern, replacement, content)
    
    # If no changes were made, try a more flexible pattern
    if modified_content == content:
        print("First pattern match failed, trying alternate pattern...")
        # More flexible pattern to match the address processing
        address_pattern2 = r"(address = clean_value\(row\.get\(col_address[^)]*\)\)[^}]+)(\s+# Basic validation\s+if not last_name or not first_name or not address:)"
        
        # Find where the basic validation starts
        validation_match = re.search(r"\s+# Basic validation\s+if not last_name or not first_name or not address:", content)
        
        if validation_match:
            # Find the address assignment before the validation
            pre_validation = content[:validation_match.start()]
            address_assignment = re.findall(r"address = [^\n]+", pre_validation)
            
            if address_assignment:
                last_assignment = address_assignment[-1]
                # Insert the address default after the last address assignment
                line_to_add = "\n                        if not address:\n                            address = \"None\"  # Set missing address to string \"None\" instead of null"
                modified_content = content.replace(last_assignment, last_assignment + line_to_add)
            else:
                print("Could not find address assignment")
                return 1
        else:
            print("Could not find validation section")
            return 1
    
    # Also modify the validation condition to check for "None" string
    validation_pattern = r"(if not last_name or not first_name or not address:)"
    validation_replacement = r"if not last_name or not first_name or (not address or address == 'None'):"
    
    # Apply validation condition change
    modified_content = re.sub(validation_pattern, validation_replacement, modified_content)
    
    # Write the modified content back to the file
    try:
        with open(views_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        print("Successfully modified driver_import function to handle missing addresses")
        return 0
    except Exception as e:
        print(f"Error writing file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 