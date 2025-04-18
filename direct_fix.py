"""
Script to fix the batch adjudication fine calculation issue in views.py
"""
import os

def fix_batch_adjudication_fine():
    file_path = 'traffic_violation_system/views.py'
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Find and replace the problematic line
    for i, line in enumerate(lines):
        if "violation.fine_amount = original_fine * (remaining_count / len(original_types))" in line:
            # Found the line that adjusts fine proportionally - comment it out
            lines[i] = "                # Line removed to fix batch amount issue - original fine preserved\n"
            # lines[i] = "                # " + line.strip() + "\n"
            print(f"Found and commented out proportional fine adjustment at line {i+1}")
    
    # Backup the original file
    backup_path = file_path + '.bak'
    with open(backup_path, 'w', encoding='utf-8') as backup:
        backup.writelines(lines)
    
    # Write the modified content to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)
    
    print(f"Successfully updated {file_path}. Original file backed up to {backup_path}")
    return True

if __name__ == "__main__":
    fix_batch_adjudication_fine() 