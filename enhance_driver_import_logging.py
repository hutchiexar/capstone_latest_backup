#!/usr/bin/env python3
"""
Script to enhance error logging in the driver_import function
"""
import re
import os
import sys

def main():
    views_path = 'traffic_violation_system/views.py'
    backup_path = 'traffic_violation_system/views.py.bak_logging'
    
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
    
    # Find the exception handler in the driver_import function
    exception_handler_pattern = r'except Exception as e:\s+error_count \+= 1\s+error_messages\.append\(f"Row \{index\+1\}: \{str\(e\)\}"\)\s+logger\.error\(f"Error importing driver \{last_name\}, \{first_name\}: \{str\(e\)\}"\)'
    
    # Create enhanced exception handler with more details
    enhanced_handler = """except Exception as e:
                            error_count += 1
                            error_detail = str(e)
                            error_type = type(e).__name__
                            
                            # Log additional details for troubleshooting
                            logger.error(f"---DRIVER IMPORT ERROR---")
                            logger.error(f"Row {index+1}: {error_type}: {error_detail}")
                            logger.error(f"Driver: {last_name}, {first_name}")
                            logger.error(f"Data: last_name={last_name}, first_name={first_name}, middle_initial={middle_initial}, address={address}, old_pd_number={old_pd_number}, new_pd_number={new_pd_number}")
                            logger.error(f"Raw data: {dict(row)}")
                            logger.error(f"Exception type: {error_type}")
                            logger.error(f"Exception detail: {error_detail}")
                            logger.error(f"---END DRIVER IMPORT ERROR---")
                            
                            # Add more detailed error to the error messages
                            error_messages.append(f"Row {index+1}: {error_type}: {error_detail}")"""
    
    # Replace the exception handler
    modified_contents = re.sub(exception_handler_pattern, enhanced_handler, contents)
    
    # Also enhance the main try/except block for file processing
    file_exception_pattern = r'except Exception as e:\s+os\.unlink\(temp_file\.name\)  # Delete temp file\s+logger\.error\(f"Error processing file: \{str\(e\)\}"\)\s+messages\.error\(request, f"Error processing file: \{str\(e\)\}"\)\s+return redirect\(\'driver_import\'\)'
    
    enhanced_file_handler = """except Exception as e:
                os.unlink(temp_file.name)  # Delete temp file
                error_type = type(e).__name__
                error_detail = str(e)
                
                # Log additional details about the file processing error
                logger.error(f"---FILE PROCESSING ERROR---")
                logger.error(f"Error type: {error_type}")
                logger.error(f"Error detail: {error_detail}")
                logger.error(f"File name: {import_file.name}, Size: {import_file.size}")
                logger.error(f"Exception info: {sys.exc_info()}")
                logger.error(f"---END FILE PROCESSING ERROR---")
                
                messages.error(request, f"Error processing file: {error_type}: {error_detail}")
                return redirect('driver_import')"""
    
    # Replace the file exception handler
    modified_contents = re.sub(file_exception_pattern, enhanced_file_handler, modified_contents)
    
    # Check if we made changes
    if modified_contents != contents:
        # Add import sys at the top if not present
        if "import sys" not in modified_contents:
            modified_contents = modified_contents.replace("import os", "import os\nimport sys")
        
        # Write the modified file
        try:
            with open(views_path, 'w', encoding='utf-8') as f:
                f.write(modified_contents)
            print(f"Successfully enhanced error logging in {views_path}")
            return 0
        except Exception as e:
            print(f"Error writing file: {e}")
            return 1
    else:
        print("No changes made to the file - patterns not found")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 