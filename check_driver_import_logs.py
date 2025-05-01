#!/usr/bin/env python3
"""
Script to check recent driver import logs in the database
"""
import os
import sys
import django
import pandas as pd

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CAPSTONE_PROJECT.settings')
django.setup()

# Import models
from traffic_violation_system.models import ActivityLog, Driver
from django.db.models import Q

def validate_driver_data(data):
    """
    Validate driver data before creating or updating a record
    Returns a tuple of (is_valid, error_message)
    """
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

def check_activity_logs():
    """Check recent activity logs related to driver imports"""
    print("Recent driver import activity logs:")
    print("-" * 80)
    
    # Get recent driver import activity logs
    logs = ActivityLog.objects.filter(
        Q(action__icontains='imported driver') | 
        Q(action__icontains='driver import') |
        Q(category='driver')
    ).order_by('-timestamp')[:20]
    
    if not logs:
        print("No recent driver import logs found")
        return
    
    for log in logs:
        print(f"[{log.timestamp}] {log.user}: {log.action}")
    
    print("\n")
    print("Checking driver validation issues:")
    print("-" * 80)
    
    # Try to find potential data quality issues in drivers
    # Check for drivers with NaN or empty values in important fields
    drivers_with_issues = Driver.objects.filter(
        Q(last_name__isnull=True) | 
        Q(last_name='') | 
        Q(first_name__isnull=True) | 
        Q(first_name='') |
        Q(address__isnull=True) |
        Q(address='')
    )[:50]
    
    if drivers_with_issues:
        print(f"Found {drivers_with_issues.count()} drivers with potential validation issues:")
        for driver in drivers_with_issues:
            print(f"ID: {driver.id}, Name: {driver.last_name}, {driver.first_name}, "
                  f"Address: {driver.address or 'None'}, PD#: {driver.new_pd_number or 'None'}")
    else:
        print("No drivers with basic validation issues found")
        
    # Check for duplicate PD numbers
    print("\nChecking for duplicate PD numbers:")
    print("-" * 80)
    
    # This query finds drivers with the same new_pd_number (where not null)
    duplicates = Driver.objects.exclude(new_pd_number__isnull=True).exclude(new_pd_number='')
    
    # Dictionary to count occurrences of each PD number
    pd_count = {}
    for driver in duplicates:
        pd_num = driver.new_pd_number
        if pd_num in pd_count:
            pd_count[pd_num] += 1
        else:
            pd_count[pd_num] = 1
    
    # Filter those with count > 1 (duplicates)
    duplicate_pds = {pd_num: count for pd_num, count in pd_count.items() if count > 1}
    
    if duplicate_pds:
        print(f"Found {len(duplicate_pds)} duplicate PD numbers:")
        for pd_num, count in duplicate_pds.items():
            print(f"PD# {pd_num}: {count} occurrences")
            # Show the actual drivers with this PD number
            drivers = Driver.objects.filter(new_pd_number=pd_num)
            for i, driver in enumerate(drivers):
                print(f"   {i+1}. {driver.last_name}, {driver.first_name} (ID: {driver.id})")
    else:
        print("No duplicate PD numbers found")
    
    # Try to find the exact failing row by examining a sample Excel file
    print("\nChecking sample file for potential issues:")
    print("-" * 80)
    
    # Try to locate a sample file (assuming it might be in the project directory)
    sample_files = ['POTPOT-DRIVERS-OPERATORS.xlsx', 'drivers.xlsx', 'operators.xlsx', 'driver_import.xlsx']
    sample_file = None
    
    for file in sample_files:
        if os.path.exists(file):
            sample_file = file
            break
    
    if sample_file:
        print(f"Found sample file: {sample_file}")
        try:
            df = pd.read_excel(sample_file)
            print(f"File contains {len(df)} rows and {len(df.columns)} columns")
            print(f"Column names: {df.columns.tolist()}")
            
            # Check each row for validation issues
            for index, row in df.iterrows():
                # Get data in a format similar to what the application uses
                try:
                    driver_data = {
                        'last_name': str(row.iloc[0]) if not pd.isna(row.iloc[0]) else None,
                        'first_name': str(row.iloc[1]) if not pd.isna(row.iloc[1]) else None,
                        'middle_initial': str(row.iloc[2]) if not pd.isna(row.iloc[2]) else None,
                        'address': str(row.iloc[3]) if not pd.isna(row.iloc[3]) else None,
                        'old_pd_number': str(row.iloc[4]) if not pd.isna(row.iloc[4]) else None,
                        'new_pd_number': str(row.iloc[5]) if not pd.isna(row.iloc[5]) else None,
                    }
                    
                    # Validate the data
                    is_valid, validation_error = validate_driver_data(driver_data)
                    
                    if not is_valid:
                        print(f"Row {index+1} has validation issues: {validation_error}")
                        print(f"  Data: {driver_data}")
                    
                    # Check for duplicate PD number
                    if driver_data.get('new_pd_number') and driver_data['new_pd_number'] != 'None':
                        # Check if this new_pd_number exists in the database multiple times
                        existing_count = Driver.objects.filter(new_pd_number=driver_data['new_pd_number']).count()
                        if existing_count > 1:
                            print(f"Row {index+1} has duplicate PD number: {driver_data['new_pd_number']} (found {existing_count} times in DB)")
                    
                except Exception as e:
                    print(f"Error processing row {index+1}: {e}")
            
        except Exception as e:
            print(f"Error reading sample file: {e}")
    else:
        print("No sample file found. Please provide a path to the Excel file used for import.")

if __name__ == "__main__":
    check_activity_logs() 