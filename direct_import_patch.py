#!/usr/bin/env python3
"""
Direct import patching script that modifies Python files to use fallback implementations.

This script can be run during the build process to patch problematic imports.
"""

import os
import sys
import re
import logging
from collections import namedtuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('import_patcher')

PatchRule = namedtuple('PatchRule', ['file_path', 'import_pattern', 'replacement'])

# Define patch rules
PATCH_RULES = [
    # idanalyzer patch
    PatchRule(
        file_path='traffic_violation_system/views.py',
        import_pattern=r'from\s+idanalyzer\s+import\s+CoreAPI',
        replacement='''# Graceful degradation for idanalyzer import
try:
    from idanalyzer import CoreAPI
except ImportError:
    # Fallback implementation
    class CoreAPI:
        def __init__(self, *args, **kwargs):
            print("WARNING: Using dummy CoreAPI. ID analysis functionality is disabled.")
            self.api_key = kwargs.get('api_key', 'dummy-key')
            self.region = kwargs.get('region', 'us')
        
        def scan(self, document_primary=None, **kwargs):
            print("INFO: Dummy ID scan requested - returning mock data")
            return {
                "success": False,
                "error": {
                    "code": "IDANALYZER_NOT_AVAILABLE",
                    "message": "ID Analyzer module is not available. This is a dummy implementation."
                }
            }
        
        def setFaceThreshold(self, threshold): pass
        def enableAuthentication(self, enable=True): pass
        def enableImageOutput(self, enable=True): pass
'''
    ),
    
    # xlsxwriter patch
    PatchRule(
        file_path='traffic_violation_system/adjudication_history_views.py',
        import_pattern=r'import\s+xlsxwriter',
        replacement='''# Graceful degradation for xlsxwriter import
try:
    import xlsxwriter
except ImportError:
    # Use our fallback implementation
    from handle_xlsxwriter import get_workbook_class
    # This is used later in the code when Workbook is accessed
    class xlsxwriter:
        @staticmethod
        def Workbook(*args, **kwargs):
            Workbook = get_workbook_class()
            return Workbook(*args, **kwargs)
'''
    )
]

def apply_patches(dry_run=False):
    """Apply all patches to the target files."""
    results = []
    
    for rule in PATCH_RULES:
        if not os.path.exists(rule.file_path):
            logger.warning(f"File not found: {rule.file_path}")
            results.append((rule.file_path, False, "File not found"))
            continue
        
        # Read file content
        try:
            with open(rule.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {rule.file_path}: {str(e)}")
            results.append((rule.file_path, False, f"Read error: {str(e)}"))
            continue
        
        # Create backup
        backup_path = f"{rule.file_path}.bak"
        if not dry_run:
            try:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                logger.error(f"Error creating backup {backup_path}: {str(e)}")
                results.append((rule.file_path, False, f"Backup error: {str(e)}"))
                continue
        
        # Apply patch
        match = re.search(rule.import_pattern, content)
        if not match:
            logger.warning(f"Import pattern not found in {rule.file_path}")
            results.append((rule.file_path, False, "Import pattern not found"))
            continue
        
        # Calculate replacement
        replacement = rule.replacement
        if 'pyhanko import' in rule.import_pattern:
            # Special handling for pyHanko import to preserve the rest of the import line
            import_line = match.group(0)
            replacement = replacement.replace('from pyhanko import', import_line)
        
        # Apply replacement
        patched_content = content.replace(match.group(0), replacement)
        
        # Write patched file
        if not dry_run:
            try:
                with open(rule.file_path, 'w', encoding='utf-8') as f:
                    f.write(patched_content)
                logger.info(f"Successfully patched {rule.file_path}")
                results.append((rule.file_path, True, "Success"))
            except Exception as e:
                logger.error(f"Error writing to {rule.file_path}: {str(e)}")
                results.append((rule.file_path, False, f"Write error: {str(e)}"))
                # Try to restore backup
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f_in:
                        with open(rule.file_path, 'w', encoding='utf-8') as f_out:
                            f_out.write(f_in.read())
                except:
                    logger.critical(f"Failed to restore backup for {rule.file_path}")
        else:
            logger.info(f"Would patch {rule.file_path} (dry run)")
            results.append((rule.file_path, True, "Dry run"))
    
    return results

if __name__ == "__main__":
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        logger.info("Running in dry-run mode - no changes will be made")
    
    # Apply patches
    results = apply_patches(dry_run)
    
    # Summarize results
    success_count = sum(1 for _, success, _ in results if success)
    logger.info(f"Patch summary: {success_count}/{len(results)} successful")
    
    # Exit with appropriate code
    sys.exit(0 if success_count == len(results) else 1) 