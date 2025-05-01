# This script changes REGULAR to NCAP in upload_violation
with open('traffic_violation_system/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Function to find a specific section and replace within that section
def replace_in_section(content, section_marker, old_text, new_text):
    sections = content.split(section_marker)
    if len(sections) > 1:
        # Replace only in the first section after the marker
        before = sections[0]
        target_section = sections[1]
        after = section_marker.join(sections[2:]) if len(sections) > 2 else ""
        
        # Replace in the target section
        modified_section = target_section.replace(old_text, new_text)
        
        # Reassemble
        return before + section_marker + modified_section + (section_marker + after if after else "")
    return content

# Find the upload_violation function and change its REGULAR to NCAP
if "def upload_violation" in content:
    print("Found upload_violation function")
    # Use section marker to ensure we only change the right instance
    content = replace_in_section(
        content, 
        "def upload_violation", 
        "classification='REGULAR'", 
        "classification='NCAP'"
    )
    
    with open('traffic_violation_system/views.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Fixed upload_violation view to use NCAP violations")
else:
    print("Could not find the upload_violation function") 