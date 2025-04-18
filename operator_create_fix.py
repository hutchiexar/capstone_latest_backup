#!/usr/bin/env python3
"""
Fix for the operator creation code in views.py to ensure unique PD numbers.

This script directly modifies the operator_application_review function to make
sure all created operators have unique PD number fields to prevent database errors.
"""

def apply_fix():
    import re
    
    # Path to the views.py file
    views_path = "traffic_violation_system/views.py"
    
    # Read the file content
    with open(views_path, 'r') as f:
        content = f.read()
    
    # Import uuid if not already present
    if "import uuid" not in content:
        # Find a good place to add the import
        import_section = content.find("import logging")
        if import_section >= 0:
            content = content[:import_section + len("import logging")] + "\nimport uuid" + content[import_section + len("import logging"):]
        else:
            # Add to the beginning if needed
            content = "import uuid\n" + content
    
    # Find the operator creation code
    old_code = re.search(r"# Get user profile for address and other details.*?operator, created = Operator\.objects\.get_or_create\(\s*user=application\.user,\s*defaults=\{[^}]*}\s*\)", content, re.DOTALL)
    
    if old_code:
        # Replace with new code that ensures unique PD numbers
        new_code = """                    # Get user profile for address and other details
                    user_profile = application.user.userprofile
                    
                    # Generate unique PD numbers to prevent database constraint errors
                    unique_prefix = f"OP-{uuid.uuid4().hex[:8]}"
                    
                    # Create or update operator record with safe attribute access
                    operator, created = Operator.objects.get_or_create(
                        user=application.user,
                        defaults={
                            'first_name': application.user.first_name,
                            'last_name': application.user.last_name,
                            'address': user_profile.address,
                            'new_pd_number': f"{unique_prefix}-NEW",  # Unique value for new_pd_number
                            'old_pd_number': f"{unique_prefix}-OLD",  # Unique value for old_pd_number
                        }
                    )"""
        
        # Apply the replacement
        modified_content = content.replace(old_code.group(0), new_code)
        
        # Write back to the file
        with open(views_path, 'w') as f:
            f.write(modified_content)
        
        print("✅ Successfully applied fix to operator creation code!")
        return True
    else:
        print("❌ Could not find the operator creation code to modify.")
        return False

if __name__ == "__main__":
    apply_fix() 