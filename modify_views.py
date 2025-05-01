#!/usr/bin/env python3
"""
Script to modify traffic_violation_system/views.py to properly handle 'nan' values
in the driver_import function
"""
import re
import sys
import os

def main():
    views_path = 'traffic_violation_system/views.py'
    backup_path = 'traffic_violation_system/views.py.bak2'
    
    # First, create a backup
    print(f"Creating backup at {backup_path}")
    try:
        with open(views_path, 'r', encoding='utf-8') as f:
            contents = f.read()
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(contents)
    except Exception as e:
        print(f"Error creating backup: {e}")
        return 1
    
    # Find the clean_value function
    clean_value_func = """
def clean_value(value):
    \"\"\"
    Helper function to handle 'nan' values from pandas DataFrame
    Returns None for pandas NaN values or string 'nan'/'NaN'
    \"\"\"
    # Check if the value is NaN using pandas isna()
    if pd.isna(value):
        return None
    
    # Convert to string and check for 'nan' string representation
    if isinstance(value, str) and value.strip().lower() == 'nan':
        return None
    
    # Return the original value if it's not NaN
    return value
"""
    
    # Add the clean_value function before driver_import
    driver_import_pattern = r'@login_required\s+def driver_import\(request\):'
    
    if re.search(driver_import_pattern, contents):
        print("Found driver_import function pattern")
    else:
        print("driver_import pattern not found")
        # Try a simpler pattern
        driver_import_pattern = '@login_required\ndef driver_import(request):'
        if driver_import_pattern in contents:
            print("Found simple driver_import function pattern")
        else:
            print("Simple driver_import pattern not found")
            return 1
    
    new_contents = re.sub(driver_import_pattern, clean_value_func + "\n@login_required\ndef driver_import(request):", contents)
    
    # Check if the clean_value function was added correctly
    if 'def clean_value(value):' in new_contents:
        print("Successfully added clean_value function")
    else:
        print("Failed to add clean_value function")
        return 1
    
    # Now find and replace the data extraction code
    # Extract a small unique identifier to find the extraction section
    extract_marker = '# Extract data'
    
    print(f"Searching for extraction marker: '{extract_marker}'")
    if extract_marker in new_contents:
        print("Found extraction marker")
        
        # Read the file line by line to find the extraction block
        lines = new_contents.split('\n')
        start_line = -1
        for i, line in enumerate(lines):
            if extract_marker in line:
                start_line = i
                print(f"Found extraction block at line {start_line}")
                break
        
        if start_line != -1:
            # Print a few lines around the extraction block for debugging
            print("Lines around extraction block:")
            for i in range(max(0, start_line-1), min(len(lines), start_line+7)):
                print(f"{i}: {lines[i]}")
            
            # Replacement with clean_value function
            replacement = """# Extract data and clean nan values
                        last_name = clean_value(row.get(col_last_name, ''))
                        if last_name:
                            last_name = str(last_name).strip()
                        
                        first_name = clean_value(row.get(col_first_name, ''))
                        if first_name:
                            first_name = str(first_name).strip()
                        
                        middle_initial = clean_value(row.get(col_middle_initial, '')) if col_middle_initial else None
                        if middle_initial:
                            middle_initial = str(middle_initial).strip()
                        
                        address = clean_value(row.get(col_address, '')) if col_address else None
                        if address:
                            address = str(address).strip()
                        
                        old_pd_number = clean_value(row.get(col_old_pd, '')) if col_old_pd else None
                        if old_pd_number:
                            old_pd_number = str(old_pd_number).strip()
                        
                        new_pd_number = clean_value(row.get(col_new_pd, '')) if col_new_pd else None
                        if new_pd_number:
                            new_pd_number = str(new_pd_number).strip()"""
            
            # Find the end of the extraction block (approximately 6 lines after the marker)
            # This is where we need to be careful
            end_line = start_line
            
            # Find the end of the extraction section by looking for lines that extract data
            for i in range(start_line + 1, min(start_line + 10, len(lines))):
                if "=" in lines[i] and any(x in lines[i] for x in ["last_name", "first_name", "middle_initial", "address", "pd_number"]):
                    end_line = i
                else:
                    # If we find a line without data extraction after some extraction lines, break
                    if end_line > start_line and "=" not in lines[i]:
                        break
            
            print(f"End of extraction block detected at line {end_line}")
            
            # Replace the extraction block
            replacement_lines = replacement.split('\n')
            print(f"Replacing {end_line - start_line + 1} lines with {len(replacement_lines)} lines")
            
            lines[start_line:end_line+1] = replacement_lines
            
            modified_contents = '\n'.join(lines)
            
            # Check if the replacement was successful
            if 'clean_value(row.get(col_last_name' in modified_contents:
                print("Successfully replaced extraction block")
                
                # Remove the extra conditionals for None values in the right sections
                print("Applying final adjustments...")
                
                # Process the file more carefully line by line
                lines = modified_contents.split('\n')
                for i, line in enumerate(lines):
                    # Look for patterns in Driver.objects.create and existing driver updates
                    if 'middle_initial if middle_initial else None' in line:
                        lines[i] = line.replace('middle_initial if middle_initial else None', 'middle_initial')
                        print(f"Replaced conditional for middle_initial at line {i}")
                    
                    if 'old_pd_number if old_pd_number else None' in line:
                        lines[i] = line.replace('old_pd_number if old_pd_number else None', 'old_pd_number')
                        print(f"Replaced conditional for old_pd_number at line {i}")
                    
                    if 'new_pd_number if new_pd_number else None' in line:
                        lines[i] = line.replace('new_pd_number if new_pd_number else None', 'new_pd_number')
                        print(f"Replaced conditional for new_pd_number at line {i}")
                    
                    # Simplify new_pd_number checks
                    if 'if new_pd_number and new_pd_number.strip():' in line:
                        lines[i] = line.replace('if new_pd_number and new_pd_number.strip():', 'if new_pd_number:')
                        print(f"Simplified new_pd_number check at line {i}")
                
                final_contents = '\n'.join(lines)
                
                # Write the modified contents back
                try:
                    with open(views_path, 'w', encoding='utf-8') as f:
                        f.write(final_contents)
                    print(f"Successfully modified {views_path}")
                    return 0
                except Exception as e:
                    print(f"Error writing modified file: {e}")
                    return 1
            else:
                print("Failed to replace extraction block")
                return 1
        else:
            print("Couldn't find start of extraction block")
            return 1
    else:
        print("Extraction marker not found")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 