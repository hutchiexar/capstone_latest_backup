#!/bin/bash

# 3G Optimization Script for Traffic Violation System
# This script sets up the necessary optimizations for slow network support

echo "Starting 3G network optimization..."

# Step 1: Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install -r requirements.txt

# Step 2: Install Node dependencies
echo "Installing Node dependencies..."
npm install

# Step 3: Build minified assets
echo "Building minified assets..."
npm run build

# Step 4: Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Step 5: Create compressed files (if django-compressor is available)
if pip list | grep django-compressor > /dev/null; then
    echo "Creating compressed assets..."
    python manage.py compress --force
else
    echo "django-compressor not installed, skipping compression step."
fi

# Step 6: Optimize existing images
echo "Optimizing existing images..."
python optimize_images.py

# If not successful, print message
if [ $? -ne 0 ]; then
    echo "optimize_images.py not found. Creating it..."
    cat > optimize_images.py << 'EOL'
#!/usr/bin/env python
"""
Image optimization script for Traffic Violation System.
This script optimizes all images in the media directory.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageOps
import concurrent.futures

def optimize_image(file_path):
    """Optimize a single image file"""
    try:
        # Skip non-image files
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return False, f"Skipped: {file_path} (not an image)"
        
        # Open image
        img = Image.open(file_path)
        
        # Set maximum dimensions for large images
        max_width = 1200
        max_height = 1200
        
        # Skip if already optimized
        if img.width <= max_width and img.height <= max_height:
            return False, f"Skipped: {file_path} (already optimized)"
        
        # Resize if needed
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.LANCZOS)
        
        # Convert to RGB if RGBA to avoid issues with JPG
        if img.mode == 'RGBA' and ext in ['.jpg', '.jpeg']:
            img = img.convert('RGB')
        
        # Save optimized image
        if ext.lower() == '.png':
            img.save(file_path, optimize=True, quality=85)
        elif ext.lower() in ['.jpg', '.jpeg']:
            img.save(file_path, optimize=True, quality=80)
        else:
            img.save(file_path)
            
        orig_size = os.path.getsize(file_path) / 1024  # KB
        
        return True, f"Optimized: {file_path} (Size: {orig_size:.1f} KB)"
    except Exception as e:
        return False, f"Error optimizing {file_path}: {str(e)}"

def main():
    """Main function to optimize all images"""
    base_dir = Path(__file__).resolve().parent
    media_dir = base_dir / 'media'
    
    if not media_dir.exists():
        print(f"Media directory not found: {media_dir}")
        return
    
    print(f"Scanning for images in {media_dir}...")
    
    # Collect all image files
    image_files = []
    for root, dirs, files in os.walk(media_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                image_files.append(os.path.join(root, file))
    
    total_files = len(image_files)
    print(f"Found {total_files} image files")
    
    if total_files == 0:
        return
    
    # Optimize images in parallel
    optimized_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_file = {executor.submit(optimize_image, file): file for file in image_files}
        for future in concurrent.futures.as_completed(future_to_file):
            success, message = future.result()
            print(message)
            if success:
                optimized_count += 1
    
    print(f"Optimization complete: {optimized_count}/{total_files} images optimized")

if __name__ == "__main__":
    main()
EOL
    chmod +x optimize_images.py
    python optimize_images.py
fi

# Step 7: Update .env file to use production settings
if grep -q "DJANGO_SETTINGS_MODULE" .env; then
    sed -i 's/DJANGO_SETTINGS_MODULE=.*/DJANGO_SETTINGS_MODULE=CAPSTONE_PROJECT.production_settings/g' .env
else
    echo "DJANGO_SETTINGS_MODULE=CAPSTONE_PROJECT.production_settings" >> .env
fi

echo "Optimization complete! The system should now perform better on 3G networks."
echo "Note: You'll need to install django-compressor and whitenoise for full optimization:"
echo "  pip install django-compressor whitenoise django-redis"
echo "And add them to your INSTALLED_APPS in settings.py."
echo "Remember to restart your server to apply all changes." 