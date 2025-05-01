#!/usr/bin/env python3
"""
Script to improve validation and error handling in the driver_import function
"""
import re
import os
import sys

def main():
    views_path = 'traffic_violation_system/views.py'
    backup_path = 'traffic_violation_system/views.py.bak_fix'
    
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
    
    # Add a validation function before the driver_import function
    driver_import_pattern = r'def clean_value\(value\):'
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
    
    # Add the validation function before clean_value
    modified_contents = contents.replace(driver_import_pattern, validation_function + "\n" + driver_import_pattern)
    
    # Modify the driver creation part to include validation and better error handling
    driver_creation_pattern = r'# Create new driver\s+# Check if new_pd_number is already in use\s+if new_pd_number and Driver\.objects\.filter\(new_pd_number=new_pd_number\)\.exists\(\):\s+logger\.error\(f"PD Number \{new_pd_number\} already in use\. Skipping row \{index\+1\}"\)\s+error_count \+= 1\s+error_messages\.append\(f"Row \{index\+1\}: PD number \{new_pd_number\} is already in use"\)\s+continue\s+\s+Driver\.objects\.create\(\s+last_name=last_name,\s+first_name=first_name,\s+middle_initial=middle_initial,\s+address=address,\s+old_pd_number=old_pd_number,\s+new_pd_number=new_pd_number\s+\)\s+success_count \+= 1'
    
    enhanced_creation = """# Create new driver
                                # Check if new_pd_number is already in use
                                if new_pd_number and Driver.objects.filter(new_pd_number=new_pd_number).exists():
                                    logger.error(f"PD Number {new_pd_number} already in use. Skipping row {index+1}")
                                    error_count += 1
                                    error_messages.append(f"Row {index+1}: PD number {new_pd_number} is already in use")
                                    continue
                                
                                # Validate data before creating
                                driver_data = {
                                    'last_name': last_name,
                                    'first_name': first_name,
                                    'middle_initial': middle_initial,
                                    'address': address,
                                    'old_pd_number': old_pd_number,
                                    'new_pd_number': new_pd_number,
                                }
                                
                                is_valid, validation_error = validate_driver_data(driver_data)
                                if not is_valid:
                                    logger.error(f"Validation error in row {index+1}: {validation_error}")
                                    error_count += 1
                                    error_messages.append(f"Row {index+1}: {validation_error}")
                                    continue
                                
                                try:
                                    Driver.objects.create(
                                        last_name=last_name,
                                        first_name=first_name,
                                        middle_initial=middle_initial,
                                        address=address,
                                        old_pd_number=old_pd_number,
                                        new_pd_number=new_pd_number
                                    )
                                    success_count += 1
                                except Exception as create_error:
                                    error_type = type(create_error).__name__
                                    error_detail = str(create_error)
                                    logger.error(f"Error creating driver in row {index+1}: {error_type}: {error_detail}")
                                    error_count += 1
                                    error_messages.append(f"Row {index+1}: {error_type}: {error_detail}")"""
    
    # Replace the driver creation part
    modified_contents = re.sub(driver_creation_pattern, enhanced_creation, modified_contents)
    
    # Also enhance the driver update section
    driver_update_pattern = r'if existing_driver:\s+# Update existing driver\s+existing_driver\.last_name = last_name\s+existing_driver\.first_name = first_name\s+existing_driver\.middle_initial = middle_initial\s+existing_driver\.address = address\s+existing_driver\.old_pd_number = old_pd_number\s+\s+# Only update new_pd_number if it\'s provided and different\s+if new_pd_number and existing_driver\.new_pd_number != new_pd_number:\s+# Check if this new_pd_number is already in use by another driver\s+if Driver\.objects\.filter\(new_pd_number=new_pd_number\)\.exclude\(id=existing_driver\.id\)\.exists\(\):\s+logger\.error\(f"PD Number \{new_pd_number\} already in use by another driver\. Skipping update for driver \{last_name\}, \{first_name\}"\)\s+error_count \+= 1\s+error_messages\.append\(f"Row \{index\+1\}: PD number \{new_pd_number\} is already in use by another driver"\)\s+continue\s+existing_driver\.new_pd_number = new_pd_number\s+\s+existing_driver\.save\(\)\s+update_count \+= 1'
    
    enhanced_update = """if existing_driver:
                                # Update existing driver
                                # Validate data before updating
                                driver_data = {
                                    'last_name': last_name,
                                    'first_name': first_name,
                                    'middle_initial': middle_initial,
                                    'address': address,
                                    'old_pd_number': old_pd_number,
                                    'new_pd_number': new_pd_number if new_pd_number and existing_driver.new_pd_number != new_pd_number else existing_driver.new_pd_number,
                                }
                                
                                is_valid, validation_error = validate_driver_data(driver_data)
                                if not is_valid:
                                    logger.error(f"Validation error in row {index+1}: {validation_error}")
                                    error_count += 1
                                    error_messages.append(f"Row {index+1}: {validation_error}")
                                    continue
                                
                                existing_driver.last_name = last_name
                                existing_driver.first_name = first_name
                                existing_driver.middle_initial = middle_initial
                                existing_driver.address = address
                                existing_driver.old_pd_number = old_pd_number
                                
                                # Only update new_pd_number if it's provided and different
                                if new_pd_number and existing_driver.new_pd_number != new_pd_number:
                                    # Check if this new_pd_number is already in use by another driver
                                    if Driver.objects.filter(new_pd_number=new_pd_number).exclude(id=existing_driver.id).exists():
                                        logger.error(f"PD Number {new_pd_number} already in use by another driver. Skipping update for driver {last_name}, {first_name}")
                                        error_count += 1
                                        error_messages.append(f"Row {index+1}: PD number {new_pd_number} is already in use by another driver")
                                        continue
                                    existing_driver.new_pd_number = new_pd_number
                                
                                try:
                                    existing_driver.save()
                                    update_count += 1
                                except Exception as update_error:
                                    error_type = type(update_error).__name__
                                    error_detail = str(update_error)
                                    logger.error(f"Error updating driver in row {index+1}: {error_type}: {error_detail}")
                                    error_count += 1
                                    error_messages.append(f"Row {index+1}: {error_type}: {error_detail}")"""
    
    # Replace the driver update part
    modified_contents = re.sub(driver_update_pattern, enhanced_update, modified_contents)
    
    # Check if we made changes
    if modified_contents != contents:
        # Write the modified file
        try:
            with open(views_path, 'w', encoding='utf-8') as f:
                f.write(modified_contents)
            print(f"Successfully enhanced validation and error handling in {views_path}")
            return 0
        except Exception as e:
            print(f"Error writing file: {e}")
            return 1
    else:
        print("No changes made to the file - patterns not found")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 