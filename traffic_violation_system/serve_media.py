import os
from django.conf import settings
from whitenoise.storage import CompressedManifestStaticFilesStorage
from whitenoise.middleware import WhiteNoiseMiddleware
from django.http import Http404
from django.http import FileResponse
from pathlib import Path
import mimetypes

class MediaFileServer:
    """
    A class to handle serving media files in production environments.
    This is particularly useful for serving user-uploaded files on platforms
    like Render that don't provide easy ways to serve files from a disk.
    """
    
    @staticmethod
    def serve_media_file(request, path):
        """
        Serve a media file from the MEDIA_ROOT directory.
        
        Args:
            request: The HTTP request
            path: The file path relative to MEDIA_ROOT
            
        Returns:
            FileResponse: The file to be served
            
        Raises:
            Http404: If the file does not exist or is not accessible
        """
        # Security check - prevent path traversal attacks
        if '..' in path or path.startswith('/'):
            raise Http404("Invalid file path")
            
        # Build the absolute path to the media file
        media_path = os.path.join(settings.MEDIA_ROOT, path)
        
        # Check if the file exists
        if not os.path.exists(media_path) or not os.path.isfile(media_path):
            raise Http404(f"File not found: {path}")
            
        # Determine the content type
        content_type, encoding = mimetypes.guess_type(media_path)
        
        # If we can't determine the content type, use a safe default
        if content_type is None:
            content_type = 'application/octet-stream'
            
        # Create and return the file response
        response = FileResponse(open(media_path, 'rb'), content_type=content_type)
        
        # Set the content disposition to inline for viewing in browser
        # Use attachment if you want the browser to download the file
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(path)}"'
        
        return response 