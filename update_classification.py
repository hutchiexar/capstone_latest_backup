import re

def update_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace filter with is_ncap=True to use classification='NCAP'
    updated_content = content.replace(
        "ViolationType.objects.filter(is_active=True, is_ncap=True)",
        "ViolationType.objects.filter(is_active=True, classification='NCAP')"
    )
    
    # Replace filter with is_ncap=False to use classification='REGULAR'
    updated_content = updated_content.replace(
        "ViolationType.objects.filter(is_active=True, is_ncap=False)",
        "ViolationType.objects.filter(is_active=True, classification='REGULAR')"
    )
    
    # Replace any is_ncap JSON field with classification in JSON
    updated_content = updated_content.replace(
        "'is_ncap': vt.is_ncap",
        "'classification': vt.classification"
    )
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(updated_content)
    
    print(f"Updated {file_path}")

if __name__ == "__main__":
    update_file('traffic_violation_system/views.py') 