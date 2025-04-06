/**
 * Framer Motion Integration for Bootstrap Modals
 * 
 * This script enhances Bootstrap modals with smooth animations
 * powered by Framer Motion.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Animation configurations
    const animations = {
        fade: {
            in: {
                opacity: [0, 1],
                transition: { duration: 0.3, ease: 'ease-out' }
            },
            out: {
                opacity: [1, 0],
                transition: { duration: 0.2, ease: 'ease-in' }
            }
        },
        scale: {
            in: {
                opacity: [0, 1],
                scale: [0.9, 1],
                transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] }
            },
            out: {
                opacity: [1, 0],
                scale: [1, 0.9],
                transition: { duration: 0.2, ease: 'ease-in' }
            }
        },
        slideUp: {
            in: {
                opacity: [0, 1],
                y: [20, 0],
                transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] }
            },
            out: {
                opacity: [1, 0],
                y: [0, 20],
                transition: { duration: 0.3, ease: 'ease-in' }
            }
        },
        slideDown: {
            in: {
                opacity: [0, 1],
                y: [-20, 0],
                transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] }
            },
            out: {
                opacity: [1, 0],
                y: [0, -20],
                transition: { duration: 0.3, ease: 'ease-in' }
            }
        },
        slideLeft: {
            in: {
                opacity: [0, 1],
                x: [20, 0],
                transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] }
            },
            out: {
                opacity: [1, 0],
                x: [0, 20],
                transition: { duration: 0.3, ease: 'ease-in' }
            }
        },
        slideRight: {
            in: {
                opacity: [0, 1],
                x: [-20, 0],
                transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] }
            },
            out: {
                opacity: [1, 0],
                x: [0, -20],
                transition: { duration: 0.3, ease: 'ease-in' }
            }
        },
        spring: {
            in: {
                opacity: [0, 1],
                scale: [0.8, 1],
                transition: { 
                    duration: 0.5, 
                    ease: [0.34, 1.56, 0.64, 1]
                }
            },
            out: {
                opacity: [1, 0],
                scale: [1, 0.8],
                transition: { duration: 0.3, ease: 'ease-in' }
            }
        },
        // Add a zoom animation specifically for image modals
        zoom: {
            in: {
                opacity: [0, 1],
                scale: [0.7, 1],
                transition: { 
                    duration: 0.6, 
                    ease: [0.16, 1, 0.3, 1]
                }
            },
            out: {
                opacity: [1, 0],
                scale: [1, 0.7],
                transition: { duration: 0.3, ease: 'ease-in' }
            }
        }
    };

    // Apply animations to all modals
    function applyModalAnimations() {
        const modals = document.querySelectorAll('.modal');
        
        modals.forEach(modal => {
            // Skip if already enhanced
            if (modal.dataset.enhanced === 'true') return;
            
            // Determine animation type from data attribute or default to scale
            let animationType = modal.dataset.animation || 'scale';
            if (!animations[animationType]) animationType = 'scale';
            
            // Special handling for image preview modals
            if (modal.id === 'imagePreviewModal' || 
                modal.querySelector('.modal-body img:only-child') || 
                modal.classList.contains('image-modal')) {
                animationType = 'zoom';
            }
            
            const animation = animations[animationType];
            const dialogElement = modal.querySelector('.modal-dialog');
            
            // Store original transition for the modal backdrop
            const originalBackdropTransition = window.getComputedStyle(modal).getPropertyValue('transition');
            
            // Event handlers for modal animations
            modal.addEventListener('show.bs.modal', function() {
                // Reset any inline styles that might have been applied
                dialogElement.style.transform = '';
                dialogElement.style.opacity = '0';
                
                // Apply animation
                setTimeout(() => {
                    // Animate using Web Animations API
                    const keyframes = [
                        { opacity: animation.in.opacity[0], transform: getTransform(animation.in, 0) },
                        { opacity: animation.in.opacity[1], transform: getTransform(animation.in, 1) }
                    ];
                    
                    const options = {
                        duration: animation.in.transition.duration * 1000,
                        easing: typeof animation.in.transition.ease === 'string' 
                            ? animation.in.transition.ease 
                            : `cubic-bezier(${animation.in.transition.ease.join(',')})`,
                        fill: 'forwards'
                    };
                    
                    dialogElement.animate(keyframes, options);
                    
                    // Special handling for image modals
                    if (animationType === 'zoom' || modal.id === 'imagePreviewModal') {
                        const image = modal.querySelector('img');
                        if (image) {
                            image.classList.add('animated');
                        }
                    }
                    
                    // Add staggered animations for list items
                    setTimeout(() => {
                        const listItems = modal.querySelectorAll('.modal-list-item:not(.animated)');
                        listItems.forEach((item, index) => {
                            item.classList.add('animated');
                        });
                    }, 100);
                }, 10);
            });
            
            modal.addEventListener('hide.bs.modal', function(event) {
                // Prevent default hiding
                event.preventDefault();
                
                // Apply exit animation
                const keyframes = [
                    { opacity: animation.out.opacity[0], transform: getTransform(animation.out, 0) },
                    { opacity: animation.out.opacity[1], transform: getTransform(animation.out, 1) }
                ];
                
                const options = {
                    duration: animation.out.transition.duration * 1000,
                    easing: typeof animation.out.transition.ease === 'string' 
                        ? animation.out.transition.ease 
                        : `cubic-bezier(${animation.out.transition.ease.join(',')})`,
                    fill: 'forwards'
                };
                
                const anim = dialogElement.animate(keyframes, options);
                
                // Remove animated classes for next time
                modal.querySelectorAll('.animated').forEach(el => {
                    el.classList.remove('animated');
                });
                
                // When animation completes, hide the modal for real
                anim.onfinish = () => {
                    modal.classList.remove('show');
                    modal.style.display = 'none';
                    document.body.classList.remove('modal-open');
                    
                    // Remove backdrop
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.classList.remove('show');
                        setTimeout(() => {
                            backdrop.remove();
                        }, 150);
                    }
                    
                    // Dispatch hidden event
                    modal.dispatchEvent(new Event('hidden.bs.modal'));
                };
            });
            
            // Mark as enhanced
            modal.dataset.enhanced = 'true';
        });
    }
    
    // Helper function to generate transform string based on animation properties
    function getTransform(animation, index) {
        let transform = '';
        
        if (animation.scale) {
            transform += `scale(${animation.scale[index]}) `;
        }
        
        if (animation.x) {
            transform += `translateX(${animation.x[index]}px) `;
        }
        
        if (animation.y) {
            transform += `translateY(${animation.y[index]}px) `;
        }
        
        return transform.trim();
    }
    
    // Apply animations when DOM is ready
    applyModalAnimations();
    
    // Also apply animations to dynamically created modals
    const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            if (mutation.addedNodes.length) {
                applyModalAnimations();
            }
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Handle dynamically loaded content
    document.addEventListener('shown.bs.modal', function(e) {
        const modal = e.target;
        
        // Add animated class to images that might be loaded asynchronously
        const images = modal.querySelectorAll('img:not(.animated)');
        images.forEach(img => {
            if (img.complete) {
                img.classList.add('animated');
            } else {
                img.addEventListener('load', function() {
                    this.classList.add('animated');
                });
            }
        });
    });
    
    // Expose API for manual integration
    window.FramerMotionModals = {
        enhance: applyModalAnimations,
        animations: animations
    };
});

/**
 * Image Gallery Viewer for Violation Images
 * A lightweight and performant image viewer that works with Framer Motion
 */
function showImagesModal(violationId) {
    // Check if modal exists already
    let imageViewerModal = document.getElementById('imageViewerModal');
    
    // Create modal if it doesn't exist
    if (!imageViewerModal) {
        const modalHtml = `
        <div class="modal fade" id="imageViewerModal" tabindex="-1" aria-labelledby="imageViewerModalLabel" aria-hidden="true" data-animation="zoom">
            <div class="modal-dialog modal-md modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="imageViewerModalLabel">Violation Images</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body p-0">
                        <div class="image-gallery-container">
                            <div class="image-gallery-main">
                                <img src="" alt="Current Image" class="img-fluid main-image" id="currentGalleryImage">
                                <div class="image-controls">
                                    <button class="btn btn-light btn-circle image-nav" id="prevImage">
                                        <span class="material-icons">chevron_left</span>
                                    </button>
                                    <button class="btn btn-light btn-circle image-nav" id="nextImage">
                                        <span class="material-icons">chevron_right</span>
                                    </button>
                                </div>
                                <div class="image-zoom-controls">
                                    <button class="btn btn-light btn-circle" id="zoomIn">
                                        <span class="material-icons">add</span>
                                    </button>
                                    <button class="btn btn-light btn-circle" id="zoomOut">
                                        <span class="material-icons">remove</span>
                                    </button>
                                    <button class="btn btn-light btn-circle" id="resetZoom">
                                        <span class="material-icons">fit_screen</span>
                                    </button>
                                </div>
                            </div>
                            <div class="image-gallery-thumbnails" id="imageThumbnails"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <style>
            .image-gallery-container {
                display: flex;
                flex-direction: column;
                height: 100%;
                background-color: #111827;
                border-radius: 0 0 8px 8px;
            }
            .image-gallery-main {
                position: relative;
                height: 50vh;
                max-height: 450px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #0f172a;
                overflow: hidden;
            }
            .main-image {
                max-height: 100%;
                max-width: 100%;
                object-fit: contain;
                transition: transform 0.3s ease;
            }
            .image-gallery-thumbnails {
                display: flex;
                gap: 6px;
                padding: 10px;
                overflow-x: auto;
                background: #1e293b;
                min-height: 80px;
            }
            .gallery-thumbnail {
                width: 60px;
                height: 60px;
                border-radius: 6px;
                object-fit: cover;
                cursor: pointer;
                border: 2px solid transparent;
                opacity: 0.7;
                transition: all 0.2s ease;
            }
            .gallery-thumbnail.active {
                border-color: var(--primary-color);
                opacity: 1;
            }
            .gallery-thumbnail:hover {
                opacity: 1;
            }
            .image-controls {
                position: absolute;
                width: 100%;
                display: flex;
                justify-content: space-between;
                padding: 0 15px;
                pointer-events: none;
            }
            .image-zoom-controls {
                position: absolute;
                bottom: 15px;
                right: 15px;
                display: flex;
                gap: 6px;
            }
            .btn-circle {
                width: 36px;
                height: 36px;
                padding: 0;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(255, 255, 255, 0.2);
                backdrop-filter: blur(4px);
                color: white;
                border: none;
                pointer-events: all;
            }
            .btn-circle:hover {
                background: rgba(255, 255, 255, 0.3);
                color: white;
            }
            .image-nav {
                opacity: 0.7;
            }
            .image-nav:hover {
                opacity: 1;
            }
            #imageViewerModal .modal-header {
                background: var(--primary-color);
                color: white;
                border-bottom: none;
                padding: 0.75rem 1rem;
            }
            #imageViewerModal .btn-close {
                filter: brightness(0) invert(1);
                opacity: 0.8;
            }
            #imageViewerModal .modal-content {
                border: none;
                border-radius: 8px;
                overflow: hidden;
            }
            
            /* Image category indicator */
            .image-category {
                position: absolute;
                top: 8px;
                left: 8px;
                background: rgba(0, 0, 0, 0.6);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 500;
                backdrop-filter: blur(4px);
            }
            
            /* Make it more responsive for smaller screens */
            @media (max-width: 576px) {
                .image-gallery-main {
                    height: 40vh;
                }
                .gallery-thumbnail {
                    width: 50px;
                    height: 50px;
                }
                .btn-circle {
                    width: 32px;
                    height: 32px;
                }
                .btn-circle .material-icons {
                    font-size: 18px;
                }
            }
        </style>`;
        
        // Append modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        imageViewerModal = document.getElementById('imageViewerModal');
        
        // Apply Framer Motion animation
        setTimeout(() => applyModalAnimations(), 100);
    }
    
    // Handle API errors gracefully
    const handleApiError = (error) => {
        console.error('Error fetching violation images:', error);
        const thumbnailsContainer = document.getElementById('imageThumbnails');
        if (thumbnailsContainer) {
            thumbnailsContainer.innerHTML = '<div class="text-center p-4 text-white">Error loading images</div>';
        }
        
        // Display error in main image area
        const imageGalleryMain = document.querySelector('.image-gallery-main');
        if (imageGalleryMain) {
            imageGalleryMain.innerHTML = `
                <div class="error-container">
                    <span class="material-icons error-icon">error_outline</span>
                    <p class="error-message">Failed to load images. Please try again.</p>
                </div>
                <style>
                    .error-container {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 100%;
                        width: 100%;
                        color: white;
                        text-align: center;
                    }
                    .error-icon {
                        font-size: 48px;
                        margin-bottom: 16px;
                        color: #f44336;
                    }
                    .error-message {
                        font-size: 16px;
                        max-width: 80%;
                    }
                </style>
            `;
        }
    };
    
    // Fetch violation images with better error handling
    fetch(`/api/violations/${violationId}/images/`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const imageUrls = [];
            const imageLabels = [];
            
            // Process each possible image
            if (data.driver_photo) {
                imageUrls.push(data.driver_photo);
                imageLabels.push('Driver');
            }
            
            if (data.vehicle_photo) {
                imageUrls.push(data.vehicle_photo);
                imageLabels.push('Vehicle');
            }
            
            if (data.image) {
                imageUrls.push(data.image);
                imageLabels.push('Main');
            }
            
            if (data.secondary_photo) {
                imageUrls.push(data.secondary_photo);
                imageLabels.push('ID');
            }
            
            // If no images available
            if (imageUrls.length === 0) {
                const thumbnailsContainer = document.getElementById('imageThumbnails');
                thumbnailsContainer.innerHTML = '<div class="text-center p-4 text-white">No images available for this violation</div>';
                return;
            }
            
            // Set up thumbnails
            const thumbnailsContainer = document.getElementById('imageThumbnails');
            thumbnailsContainer.innerHTML = '';
            
            imageUrls.forEach((url, index) => {
                const thumbnail = document.createElement('img');
                thumbnail.src = url;
                thumbnail.classList.add('gallery-thumbnail', 'modal-list-item');
                thumbnail.dataset.index = index;
                thumbnail.alt = imageLabels[index];
                thumbnail.onclick = () => changeMainImage(index);
                if (index === 0) thumbnail.classList.add('active');
                thumbnailsContainer.appendChild(thumbnail);
            });
            
            // Set initial main image
            const mainImage = document.getElementById('currentGalleryImage');
            mainImage.src = imageUrls[0];
            
            // Add image category indicator
            const imageCategory = document.createElement('div');
            imageCategory.classList.add('image-category');
            imageCategory.textContent = imageLabels[0];
            
            // Remove existing indicator if any
            const existingIndicator = document.querySelector('.image-category');
            if (existingIndicator) existingIndicator.remove();
            
            // Add new indicator
            const mainImageContainer = document.querySelector('.image-gallery-main');
            mainImageContainer.appendChild(imageCategory);
            
            // Initialize image navigation
            let currentIndex = 0;
            let currentZoom = 1;
            
            // Function to change main image
            window.changeMainImage = function(index) {
                currentIndex = index;
                mainImage.src = imageUrls[index];
                
                // Reset zoom when changing images
                currentZoom = 1;
                mainImage.style.transform = `scale(${currentZoom})`;
                
                // Update active thumbnail
                document.querySelectorAll('.gallery-thumbnail').forEach(thumb => {
                    thumb.classList.remove('active');
                });
                document.querySelector(`.gallery-thumbnail[data-index="${index}"]`).classList.add('active');
                
                // Update image category
                imageCategory.textContent = imageLabels[index];
            };
            
            // Set up navigation
            document.getElementById('prevImage').onclick = function() {
                const newIndex = (currentIndex - 1 + imageUrls.length) % imageUrls.length;
                changeMainImage(newIndex);
            };
            
            document.getElementById('nextImage').onclick = function() {
                const newIndex = (currentIndex + 1) % imageUrls.length;
                changeMainImage(newIndex);
            };
            
            // Set up zoom controls
            document.getElementById('zoomIn').onclick = function() {
                currentZoom = Math.min(currentZoom + 0.25, 3);
                mainImage.style.transform = `scale(${currentZoom})`;
            };
            
            document.getElementById('zoomOut').onclick = function() {
                currentZoom = Math.max(currentZoom - 0.25, 0.5);
                mainImage.style.transform = `scale(${currentZoom})`;
            };
            
            document.getElementById('resetZoom').onclick = function() {
                currentZoom = 1;
                mainImage.style.transform = `scale(${currentZoom})`;
            };
            
            // Add keyboard navigation
            document.addEventListener('keydown', function(e) {
                if (!document.getElementById('imageViewerModal').classList.contains('show')) return;
                
                if (e.key === 'ArrowLeft') {
                    document.getElementById('prevImage').click();
                }
                else if (e.key === 'ArrowRight') {
                    document.getElementById('nextImage').click();
                }
                else if (e.key === '+' || e.key === '=') {
                    document.getElementById('zoomIn').click();
                }
                else if (e.key === '-') {
                    document.getElementById('zoomOut').click();
                }
                else if (e.key === '0') {
                    document.getElementById('resetZoom').click();
                }
            });
            
            // Apply animation to thumbnails
            setTimeout(() => {
                const thumbnails = document.querySelectorAll('.gallery-thumbnail');
                thumbnails.forEach((thumb, idx) => {
                    thumb.style.animationDelay = `${0.1 + idx * 0.05}s`;
                });
            }, 100);
        })
        .catch(handleApiError);
    
    // Show the modal
    const bsModal = new bootstrap.Modal(imageViewerModal);
    bsModal.show();
}

// Export for global scope
window.showImagesModal = showImagesModal; 