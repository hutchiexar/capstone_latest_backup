"""
Patch script to update views.py to use the handle_idanalyzer fallback mechanism.

This script should be run from the project root directory.
"""

import os
import re
import sys
import logging

logger = logging.getLogger(__name__)

def patch_views_file():
    """
    Patches traffic_violation_system/views.py to use handle_idanalyzer.
    """
    views_path = os.path.join('traffic_violation_system', 'views.py')
    if not os.path.exists(views_path):
        logger.error(f"Cannot find views file at {views_path}")
        return False
    
    backup_path = views_path + '.backup'
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Pattern to find the idanalyzer import
    import_pattern = r'from idanalyzer import CoreAPI'
    if not re.search(import_pattern, content):
        logger.error("Could not find idanalyzer import in views.py")
        return False
    
    # Replace the import with our fallback mechanism
    new_import = 'from handle_idanalyzer import get_core_api\n# Original: from idanalyzer import CoreAPI\nCoreAPI = get_core_api()'
    patched_content = re.sub(import_pattern, new_import, content)
    
    # Write the patched file
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(patched_content)
    
    logger.info(f"Successfully patched {views_path} to use handle_idanalyzer")
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = patch_views_file()
    sys.exit(0 if success else 1) 