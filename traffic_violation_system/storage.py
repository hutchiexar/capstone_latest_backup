from django.core.files.storage import FileSystemStorage
import os
import re
from django.conf import settings
import uuid

class SafeFileStorage(FileSystemStorage):
    """
    A custom storage class that ensures filenames are valid for the filesystem.
    - Limits filename length
    - Removes special characters
    - Preserves file extensions
    - Uses UUID for uniqueness
    """
    
    def get_valid_name(self, name):
        """
        Return a filename that's safe for the underlying file system.
        """
        # Get the extension
        ext = os.path.splitext(name)[1].lower()
        if not ext:
            ext = '.jpg'  # Default extension
            
        # Remove special characters and limit filename length
        s = re.sub(r'[^\w\s.-]', '', name).strip()
        s = re.sub(r'\s+', '_', s)
        
        # If filename is still too long, use UUID
        if len(s) > 50:
            s = f"file_{uuid.uuid4().hex[:10]}"
            
        return f"{s}{ext}"
    
    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's available in the storage mechanism.
        """
        name = self.get_valid_name(name)
        if max_length and len(name) > max_length:
            # Truncate to max_length - 10 to allow for a unique suffix
            name_without_extension, extension = os.path.splitext(name)
            max_len = max_length - len(extension) - 10
            name = f"{name_without_extension[:max_len]}_{uuid.uuid4().hex[:8]}{extension}"
            
        return super().get_available_name(name, max_length) 