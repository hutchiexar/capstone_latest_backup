import re

# Read the file
with open('views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section where we extract the data
extract_pattern = re.compile(r'(\s+# Process each row.*?continue\n\n\s+# Extract data\n)(\s+last_name = str\(row\.get\(col_last_name, \'\'\)\)\.strip\(\).*?\n\s+first_name = str\(row\.get\(col_first_name, \'\'\)\)\.strip\(\).*?\n\s+middle_initial = str\(row\.get\(col_middle_initial, \'\'\)\)\.strip\(\) if col_middle_initial else None\n\s+address = str\(row\.get\(col_address, \'\'\)\)\.strip\(\)\n\s+old_pd_number = str\(row\.get\(col_old_pd, \'\'\)\)\.strip\(\) if col_old_pd else None\n\s+new_pd_number = str\(row\.get\(col_new_pd, \'\'\)\)\.strip\(\) if col_new_pd else None)', re.DOTALL)

# Define the replacement with the nan handling function
replacement = r'\1                        # Helper function to handle nan values\n                        def clean_value(value):\n                            if pd.isna(value) or str(value).lower() == \'nan\':\n                                return None\n                            return str(value).strip()\n                        \n                        # Extract data with nan handling\n                        last_name = clean_value(row.get(col_last_name, \'\')) or \'\'\n                        first_name = clean_value(row.get(col_first_name, \'\')) or \'\'\n                        middle_initial = clean_value(row.get(col_middle_initial, \'\')) if col_middle_initial else None\n                        address = clean_value(row.get(col_address, \'\')) or \'\'\n                        old_pd_number = clean_value(row.get(col_old_pd, \'\')) if col_old_pd else None\n                        new_pd_number = clean_value(row.get(col_new_pd, \'\')) if col_new_pd else None'

# Replace in content
new_content = extract_pattern.sub(replacement, content)

# Write back to the file
if content != new_content:
    with open('views.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully updated views.py to handle 'nan' values.")
else:
    print("No changes made. Pattern not found.") 