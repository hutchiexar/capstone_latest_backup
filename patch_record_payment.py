"""
This script patches the record_payment function in views.py to add the receipt_url to the JSON response
"""
import re
import os

def patch_views_file():
    # Path to the views file
    views_file = 'traffic_violation_system/views.py'
    
    # Read the current content
    with open(views_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Define the pattern to match (the JSON response in record_payment)
    # This matches the specific JsonResponse pattern we want to modify
    pattern = r"return JsonResponse\(\{\s*'success': True,\s*'message': 'Payment recorded successfully'\s*\}\)"
    
    # Define the replacement (with receipt_url added)
    replacement = "return JsonResponse({\n                    'success': True,\n                    'message': 'Payment recorded successfully',\n                    'receipt_url': reverse('receipt_summary', args=[violation.id])\n                })"
    
    # Replace the pattern with the updated code
    updated_content = re.sub(pattern, replacement, content)
    
    # Check if any changes were made
    if content == updated_content:
        print("No changes were made. Pattern not found.")
        
        # Try a more flexible pattern
        pattern2 = r"return JsonResponse\(\{\s*['|\"]success['|\"]: True,\s*['|\"]message['|\"]: ['|\"]Payment recorded successfully['|\"]\s*\}\)"
        updated_content = re.sub(pattern2, replacement, content)
        
        if content == updated_content:
            print("Second pattern also not found.")
            return False
    
    # Write the updated content back to the file
    with open(views_file, 'w', encoding='utf-8') as file:
        file.write(updated_content)
    
    print(f"Successfully updated {views_file}")
    return True

if __name__ == "__main__":
    patch_views_file() 