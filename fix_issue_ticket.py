# This script changes NCAP to REGULAR in issue_ticket
with open('traffic_violation_system/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the issue_ticket function and change its NCAP to REGULAR
# We assume this appears only once in the file
if "def issue_ticket" in content and "classification='NCAP'" in content:
    fixed_content = content.replace("classification='NCAP'", "classification='REGULAR'")
    
    with open('traffic_violation_system/views.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
        
    print("Fixed issue_ticket view to use REGULAR violations")
else:
    print("Could not find the correct pattern to replace") 