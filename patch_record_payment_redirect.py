"""
This script patches the record_payment function in views.py to redirect to receipt_summary for form submissions
"""
import re
import os

def patch_views_file():
    # Path to the views file
    views_file = 'traffic_violation_system/views.py'
    
    # Read the current content
    with open(views_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Define the pattern to match (the redirect in record_payment)
    pattern = r"return redirect\('payment_processing'\)"
    
    # Define the replacement (with redirect to receipt_summary)
    replacement = "return redirect('receipt_summary', violation_id=violation.id)"
    
    # Replace the pattern with the updated code
    updated_content = re.sub(pattern, replacement, content)
    
    # Check if any changes were made
    if content == updated_content:
        print("No changes were made. Pattern not found.")
        return False
    
    # Write the updated content back to the file
    with open(views_file, 'w', encoding='utf-8') as file:
        file.write(updated_content)
    
    print(f"Successfully updated {views_file}")
    return True

if __name__ == "__main__":
    patch_views_file() 