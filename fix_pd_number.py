#!/usr/bin/env python3
"""
Fix for the operator approval database error.

This script edits the views.py file to ensure unique PD numbers for operators
to prevent duplicate key errors.
"""

import re
import sys
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_operator_creation(views_path):
    """
    Read the views.py file, find the problematic code, and fix it.
    """
    try:
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the code block with operator creation
        original_snippet = """                    operator, created = Operator.objects.get_or_create(
                        user=application.user,
                        defaults={
                            'first_name': application.user.first_name,
                            'last_name': application.user.last_name,
                            'address': user_profile.address,
                            'new_pd_number': getattr(application, 'new_pd_number', 'New'),
                            'old_pd_number': getattr(application, 'old_pd_number', ''),
                        }
                    )"""
        
        fixed_snippet = """                    # Generate unique values for PD number fields to avoid database constraint errors
                    unique_prefix = f"OP-{uuid.uuid4().hex[:8]}"
                    operator, created = Operator.objects.get_or_create(
                        user=application.user,
                        defaults={
                            'first_name': application.user.first_name,
                            'last_name': application.user.last_name,
                            'address': user_profile.address,
                            'new_pd_number': f"{unique_prefix}-NEW",  # Ensure unique value
                            'old_pd_number': f"{unique_prefix}-OLD" if getattr(application, 'old_pd_number', '') else '',
                        }
                    )"""
        
        if original_snippet in content:
            # Replace with the fixed version
            modified_content = content.replace(original_snippet, fixed_snippet)
            
            # Add the uuid import if not already present
            if "import uuid" not in modified_content:
                import_line = "import uuid"
                # Find a good spot to add the import (after other imports)
                import_section_end = modified_content.find("from django.contrib.auth.decorators")
                if import_section_end > 0:
                    modified_content = modified_content[:import_section_end] + import_line + "\n" + modified_content[import_section_end:]
                else:
                    # Just add it at the top as a fallback
                    modified_content = import_line + "\n" + modified_content
            
            # Write the modified content back
            with open(views_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            logger.info("✅ Successfully fixed operator PD number fields to ensure uniqueness")
            return True
        else:
            modified_snippet = """                    # Generate unique values for PD number fields to avoid database constraint errors
                    operator, created = Operator.objects.get_or_create(
                        user=application.user,
                        defaults={
                            'first_name': application.user.first_name,
                            'last_name': application.user.last_name,
                            'address': user_profile.address,
                        }
                    )"""
            
            if modified_snippet in content:
                logger.info("⚠️ Previous fix was applied but was insufficient. Applying more robust fix.")
                # Apply the new fix that includes unique values
                modified_content = content.replace(modified_snippet, fixed_snippet)
                
                # Add the uuid import if not already present
                if "import uuid" not in modified_content:
                    import_line = "import uuid"
                    import_section_end = modified_content.find("from django.contrib.auth.decorators")
                    if import_section_end > 0:
                        modified_content = modified_content[:import_section_end] + import_line + "\n" + modified_content[import_section_end:]
                    else:
                        modified_content = import_line + "\n" + modified_content
                
                with open(views_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                logger.info("✅ Successfully applied more robust fix for operator PD number fields")
                return True
            else:
                logger.error("⚠️ Could not find the problematic code block. The file may have been modified.")
                return False
    
    except Exception as e:
        logger.error(f"❌ Error fixing operator creation: {str(e)}")
        return False

if __name__ == "__main__":
    views_path = "traffic_violation_system/views.py"
    if len(sys.argv) > 1:
        views_path = sys.argv[1]
    
    success = fix_operator_creation(views_path)
    sys.exit(0 if success else 1) 