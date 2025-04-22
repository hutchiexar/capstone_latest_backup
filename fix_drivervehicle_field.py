#!/usr/bin/env python

# Script to fix DriverVehicleAssignment field error 
# Replaces 'active' with 'is_active' in DriverVehicleAssignment queries

import re

# Path to the files
views_path = 'traffic_violation_system/views.py'

# Read the file
with open(views_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Replace DriverVehicleAssignment.objects.filter(driver=driver, active=True) with is_active=True
driver_vehicle_pattern = r'(DriverVehicleAssignment\.objects\.filter\([^)]*?)active=(True|False)([^)]*?\))'
fixed_content = re.sub(driver_vehicle_pattern, r'\1is_active=\2\3', content)

# Also replace unassigned_vehicles code - this is a bit more complex
unassigned_pattern = r'(id__in=DriverVehicleAssignment\.objects\.filter\(\s*active=True\s*\))'
fixed_content = re.sub(unassigned_pattern, r'id__in=DriverVehicleAssignment.objects.filter(is_active=True)', fixed_content)

# Write the updated content back to the file
with open(views_path, 'w', encoding='utf-8') as file:
    file.write(fixed_content)

print("Successfully fixed DriverVehicleAssignment field references") 