import re

# Read the current file
with open('traffic_violation_system/views_qr_code.py', 'r') as file:
    content = file.read()

# Fix the first try-except block for the profile.license_number if statement
content = re.sub(
    r"try:\s+# First try the user_account direct relationship.*?from traffic_violation_system\.models import Violation\s+# Check if user has a license number and use it to filter\s+if profile\.license_number:(.*?)else:(.*?)logger\.info",
    r"try:\n            # First try the user_account direct relationship\n            from django.db.models import Q\n            from traffic_violation_system.models import Violation\n            \n            # Check if user has a license number and use it to filter\n            if profile.license_number:\1\n            else:\2\n            logger.info",
    content, 
    flags=re.DOTALL
)

# Fix the second try-except block for the if '-' in enforcer_id: with parts.split
content = re.sub(
    r"if '-' in enforcer_id:\s+parts = enforcer_id\.split\('-'\)\s+if len\(parts\) == 2 and parts\[0\]\.isdigit\(\):",
    r"if '-' in enforcer_id:\n                            parts = enforcer_id.split('-')\n                            if len(parts) == 2 and parts[0].isdigit():",
    content
)

# Also fix the indentation for the legacy format "2-Rossvan"
content = re.sub(
    r"# APPROACH 4: Try legacy.*?if '-' in enforcer_id:(.*?)parts = enforcer_id\.split\('-'\)(.*?)if len\(parts\) == 2 and parts\[0\]\.isdigit\(\):(.*?)# This looks like \"2-Rossvan\" format",
    r"# APPROACH 4: Try legacy \"2-Rossvan\" format (digit-name format)\n                        if '-' in enforcer_id:\n                            parts = enforcer_id.split('-')\n                            if len(parts) == 2 and parts[0].isdigit():\n                                # This looks like \"2-Rossvan\" format",
    content,
    flags=re.DOTALL
)

# Fix the indentation in the qr_user_data function
content = re.sub(
    r"# APPROACH 1: Try by username.*?try:\s+user = User\.objects\.get\(username=enforcer_id\)(.*?)except \(User\.DoesNotExist, UserProfile\.DoesNotExist\):(.*?)# APPROACH 2: Try without dashes(.*?)try:\s+no_dash_id = enforcer_id\.replace",
    r"# APPROACH 1: Try by username - many QR codes might encode just the username\n            try:\n                user = User.objects.get(username=enforcer_id)\1\n            except (User.DoesNotExist, UserProfile.DoesNotExist):\2\n                # APPROACH 2: Try without dashes\3\n                try:\n                    no_dash_id = enforcer_id.replace",
    content,
    flags=re.DOTALL
)

# Write the fixed content back to the file
with open('traffic_violation_system/views_qr_code.py', 'w') as file:
    file.write(content)

print("Fixed syntax errors in traffic_violation_system/views_qr_code.py") 