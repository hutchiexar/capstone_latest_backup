#!/usr/bin/env python
"""
direct_import_patch.py

This script patches problematic imports in the codebase to include try-except blocks 
with graceful fallbacks. It identifies problematic imports using regex patterns,
backs up original files, and replaces imports with try-except blocks that include
fallback implementations.
"""

import os
import re
import shutil
import logging
from datetime import datetime

# Setup logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename=os.path.join(log_dir, f'import_patch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define patch rules
PATCH_RULES = {
    # Pattern for idanalyzer imports
    r'from\s+idanalyzer\s+import\s+CoreAPI': {
        'replacement': """
# Graceful degradation for idanalyzer import
try:
    from idanalyzer import CoreAPI
except ImportError:
    # Fallback implementation
    class CoreAPI:
        def __init__(self, *args, **kwargs):
            print("WARNING: Using dummy CoreAPI. ID analysis functionality is disabled.")
            self.args = args
            self.kwargs = kwargs
            
        def analyze(self, *args, **kwargs):
            return {
                "result": False,
                "error": {
                    "code": "import_error",
                    "message": "idanalyzer module not available in this environment"
                }
            }
"""
    },
    # Pattern for pyHanko imports
    r'from\s+pyhanko(?:\.|\s+import)': {
        'replacement': """
# Graceful degradation for pyHanko imports
try:
    from pyhanko import stamp
    from pyhanko.pdf_utils import text, images
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers, fields
    from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata
except ImportError:
    # Fallback implementation for pyHanko
    print("WARNING: pyHanko module not available. PDF signing functionality is disabled.")
    
    # Create dummy modules and classes to prevent import errors
    class DummyModule:
        def __getattr__(self, name):
            return None
    
    stamp = DummyModule()
    text = DummyModule()
    images = DummyModule()
    
    class IncrementalPdfFileWriter:
        def __init__(self, *args, **kwargs):
            pass
    
    signers = DummyModule()
    fields = DummyModule()
    
    class PdfSignatureMetadata:
        def __init__(self, *args, **kwargs):
            pass
"""
    },
    # Pattern for xlsxwriter imports
    r'import\s+xlsxwriter': {
        'replacement': """
# Graceful degradation for xlsxwriter import
try:
    import xlsxwriter
except ImportError:
    # Use a fallback implementation based on CSV
    import csv
    import io
    
    class Workbook:
        def __init__(self, filename=None):
            self.filename = filename
            self.worksheets = []
            
        def add_worksheet(self, name=None):
            worksheet = Worksheet(name)
            self.worksheets.append(worksheet)
            return worksheet
            
        def close(self):
            # Convert to CSV if filename is provided
            if self.filename and self.worksheets:
                for worksheet in self.worksheets:
                    csv_filename = f"{self.filename.rsplit('.', 1)[0]}_{worksheet.name}.csv"
                    with open(csv_filename, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        for row_idx, row in enumerate(worksheet.data):
                            if row_idx in worksheet.data:
                                writer.writerow([worksheet.data[row_idx].get(col_idx, '') for col_idx in range(worksheet.max_col)])
            
    class Worksheet:
        def __init__(self, name=None):
            self.name = name or 'Sheet'
            self.data = {}
            self.max_row = 0
            self.max_col = 0
            
        def write(self, row, col, data, cell_format=None):
            if row not in self.data:
                self.data[row] = {}
            self.data[row][col] = data
            self.max_row = max(self.max_row, row + 1)
            self.max_col = max(self.max_col, col + 1)
            
        def set_column(self, first_col, last_col, width):
            pass
            
        def write_formula(self, row, col, formula, cell_format=None, value=None):
            self.write(row, col, value or formula, cell_format)
    
    # Replace the xlsxwriter module with our fallback
    class XlsxwriterModule:
        Workbook = Workbook
        
    xlsxwriter = XlsxwriterModule()
    print("WARNING: Using CSV fallback for xlsxwriter. Excel export functionality is limited.")
"""
    }
}

def backup_file(filepath):
    """Create a backup of the file"""
    backup_path = f"{filepath}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    logging.info(f"Created backup: {backup_path}")
    return backup_path

def is_binary_file(filepath, sample_size=8192):
    """Check if a file is binary by reading a sample of its content"""
    try:
        with open(filepath, 'rb') as f:
            sample = f.read(sample_size)
            # Check for null bytes or other non-UTF-8 characters
            if b'\x00' in sample:
                return True
            try:
                sample.decode('utf-8')
                return False  # Successfully decoded as UTF-8
            except UnicodeDecodeError:
                return True  # Not a valid UTF-8 file
    except Exception as e:
        logging.warning(f"Error checking if {filepath} is binary: {str(e)}")
        return True  # Assume binary to be safe

def patch_file(filepath):
    """Patch a single file with our import replacements"""
    # Skip binary files
    if is_binary_file(filepath):
        logging.info(f"Skipping binary file: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        patched = False
        
        for pattern, rule in PATCH_RULES.items():
            if re.search(pattern, content):
                backup_file(filepath)
                content = re.sub(pattern, rule['replacement'], content)
                patched = True
                logging.info(f"Patched {pattern} in {filepath}")
        
        if patched:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except UnicodeDecodeError as e:
        logging.warning(f"Skipping file due to encoding error: {filepath}, Error: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Error processing file {filepath}: {str(e)}")
        return False

def find_python_files(directory='.'):
    """Find all Python files recursively from the given directory"""
    python_files = []
    for root, _, files in os.walk(directory):
        # Skip virtual environment directories
        if '.venv' in root or 'venv' in root or '__pycache__' in root or '.git' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    return python_files

def main():
    """Main function to patch problematic imports"""
    logging.info("Starting import patching process")
    
    # Get all Python files
    python_files = find_python_files()
    logging.info(f"Found {len(python_files)} Python files to process")
    
    # Track statistics
    patched_files = 0
    skipped_files = 0
    
    # Process each file
    for filepath in python_files:
        try:
            if patch_file(filepath):
                patched_files += 1
            else:
                skipped_files += 1
        except Exception as e:
            logging.error(f"Error processing {filepath}: {str(e)}")
            skipped_files += 1
    
    logging.info(f"Patching complete. Modified {patched_files} files, skipped {skipped_files} files.")
    print(f"Patching complete. Modified {patched_files} files, skipped {skipped_files} files.")

if __name__ == "__main__":
    main() 