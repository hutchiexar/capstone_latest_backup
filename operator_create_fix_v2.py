#!/usr/bin/env python3
"""
Script to fix operator creation in views.py by ensuring unique new_pd_number values.

The issue occurs during operator application review when creating new operators. 
The Operator model requires new_pd_number to be unique, but the current code doesn't 
ensure uniqueness in all cases, which can lead to database errors.

This script modifies the operator_application_review function to ensure that 
all created operators have unique new_pd_number fields by using uuid.
"""

import re
import os
import sys

def apply_fix():
    """
    Apply the fix to the views.py file.
    
    The fix ensures that new_pd_number is always unique by generating a UUID-based value.
    """
    try:
        # Path to views.py
        views_path = os.path.join('traffic_violation_system', 'views.py')
        
        # Read the current content of the views.py file
        with open(views_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check if uuid is already imported
        if 'import uuid' not in content:
            # Add import statement for uuid
            content = re.sub(
                r'(import os\s*(?:\n|$))', 
                r'\1import uuid\n', 
                content
            )
        
        # Original pattern to find the operator creation code
        pattern = r"""(\s+# Create or update operator record with safe attribute access\s+operator, created = Operator\.objects\.get_or_create\(\s+user=application\.user,\s+defaults=\{[^}]+\}\s+\))"""
        
        # New code with unique PD number generation
        replacement = """
                    # Create or update operator record with safe attribute access
                    # Generate unique PD numbers to prevent database constraint errors
                    unique_prefix = f"OP-{uuid.uuid4().hex[:8]}"
                    
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
        
        # Apply the fix using regex to find and replace the code
        if re.search(pattern, content, re.DOTALL):
            updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            # Save the updated content back to views.py
            with open(views_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            
            print("✅ Successfully applied fix for operator creation!")
            return True
        else:
            print("❌ Could not find the operator creation code in views.py. The pattern might have changed.")
            return False
    
    except Exception as e:
        print(f"❌ Error applying fix: {str(e)}")
        return False

if __name__ == "__main__":
    apply_fix() 