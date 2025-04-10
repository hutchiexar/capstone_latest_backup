from django.core.files.storage import FileSystemStorage
import os
import re
from django.conf import settings
import uuid
from io import BytesIO
from PIL import Image, ImageOps
import sys

class SafeFileStorage(FileSystemStorage):
    """
    A custom storage class that ensures filenames are valid for the filesystem.
    - Limits filename length
    - Removes special characters
    - Preserves file extensions
    - Uses UUID for uniqueness
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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
    
    def _save(self, name, content):
        # Check if this is an image file
        if self._is_image_file(name):
            try:
                # Optimize the image
                optimized_content = self._optimize_image(content)
                # Save the optimized image
                return super()._save(name, optimized_content)
            except Exception as e:
                print(f"Image optimization error: {str(e)}", file=sys.stderr)
                # If optimization fails, save original
                return super()._save(name, content)
        else:
            # For non-image files, save as is
            return super()._save(name, content)
    
    def _is_image_file(self, filename):
        """Check if the file is an image based on extension"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        ext = os.path.splitext(filename)[1].lower()
        return ext in image_extensions
    
    def _optimize_image(self, content):
        """Optimize an image by resizing and compressing it"""
        # Create a BytesIO object
        img_io = BytesIO()
        
        # Open the image
        img = Image.open(content)
        
        # Set maximum dimensions for large images
        max_width = 1200
        max_height = 1200
        
        # Check if resizing is needed
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.LANCZOS)
        
        # Convert to RGB if RGBA to avoid issues with JPG
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Determine image format
        format = img.format if img.format else 'JPEG'
        
        # Optimize and save
        if format.upper() == 'PNG':
            img.save(img_io, format=format, optimize=True, quality=85)
        elif format.upper() in ['JPG', 'JPEG']:
            img.save(img_io, format=format, optimize=True, quality=80)
        else:
            img.save(img_io, format=format)
        
        # Reset file pointer
        img_io.seek(0)
        
        # Create a new ContentFile
        from django.core.files.base import ContentFile
        return ContentFile(img_io.getvalue())

class RenderMediaStorage(FileSystemStorage):
    """
    Custom storage for handling media files on Render's ephemeral filesystem.
    """
    def __init__(self, *args, **kwargs):
        location = settings.MEDIA_ROOT
        # Ensure directory exists
        os.makedirs(location, exist_ok=True)
        # Set permissions
        try:
            os.chmod(location, 0o777)
        except:
            pass
        super().__init__(location=location, *args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """
        Returns a filename that's free on the target storage system.
        """
        # Make sure the directory exists
        directory = os.path.dirname(os.path.join(self.location, name))
        os.makedirs(directory, exist_ok=True)
        return super().get_available_name(name, max_length) 