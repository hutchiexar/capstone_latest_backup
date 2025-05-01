# Script to check if the error is fixed
with open('traffic_violation_system/views.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Check if the error still exists
if "classification=\\'NCAP\\'" in content:
    print("ERROR: The problem still exists. Not fixed!")
else:
    # Check if we have the correct string now
    if "classification='NCAP'" in content:
        print("SUCCESS: The file has been fixed! All occurrences of the error have been corrected.")
    else:
        print("WARNING: The error string is gone, but we don't see the expected correction either.") 