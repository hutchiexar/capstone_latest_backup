# This script fixes the quote issue in views.py
with open('traffic_violation_system/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

fixed_content = content.replace("classification=\\'NCAP\\'", "classification='NCAP'")
fixed_content = fixed_content.replace("classification=\\'REGULAR\\'", "classification='REGULAR'")

with open('traffic_violation_system/views.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("Fixed quotes in views.py") 