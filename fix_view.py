# Script to fix the syntax error in views.py
with open('traffic_violation_system/views.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Replace the problematic text
fixed_content = content.replace("classification=\\'NCAP\\'", "classification='NCAP'")

# Write the fixed content back to the file
with open('traffic_violation_system/views.py', 'w', encoding='utf-8') as file:
    file.write(fixed_content)

print("File has been fixed. All occurrences of the error have been corrected.") 