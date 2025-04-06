/**
 * Lazy Loading Implementation
 * This script implements lazy loading for images to improve performance on slow connections
 */

document.addEventListener('DOMContentLoaded', function() {
  // Check if browser supports Intersection Observer
  if ('IntersectionObserver' in window) {
    const lazyImageObserver = new IntersectionObserver(function(entries, observer) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          const lazyImage = entry.target;
          
          // Handle normal images
          if (lazyImage.dataset.src) {
            lazyImage.src = lazyImage.dataset.src;
            lazyImage.removeAttribute('data-src');
          }
          
          // Handle background images
          if (lazyImage.dataset.background) {
            lazyImage.style.backgroundImage = `url(${lazyImage.dataset.background})`;
            lazyImage.removeAttribute('data-background');
          }
          
          lazyImage.classList.remove('lazy-load');
          lazyObserver.unobserve(lazyImage);
        }
      });
    }, {
      rootMargin: '200px 0px', // Load images 200px before they appear in viewport
      threshold: 0.01
    });
    
    // Observe all elements with the lazy-load class
    const lazyImages = document.querySelectorAll('.lazy-load');
    lazyImages.forEach(function(lazyImage) {
      lazyObserver.observe(lazyImage);
    });
  } else {
    // Fallback for browsers that don't support Intersection Observer
    function lazyLoadImages() {
      const lazyImages = document.querySelectorAll('.lazy-load');
      const windowHeight = window.innerHeight;
      
      lazyImages.forEach(function(lazyImage) {
        const rect = lazyImage.getBoundingClientRect();
        
        // Check if image is near the viewport
        if (rect.top <= windowHeight + 200 && rect.bottom >= -200) {
          if (lazyImage.dataset.src) {
            lazyImage.src = lazyImage.dataset.src;
            lazyImage.removeAttribute('data-src');
          }
          
          if (lazyImage.dataset.background) {
            lazyImage.style.backgroundImage = `url(${lazyImage.dataset.background})`;
            lazyImage.removeAttribute('data-background');
          }
          
          lazyImage.classList.remove('lazy-load');
        }
      });
      
      // If all images have been loaded, remove the scroll event listener
      if (document.querySelectorAll('.lazy-load').length === 0) {
        window.removeEventListener('scroll', throttledLazyLoad);
        window.removeEventListener('resize', throttledLazyLoad);
      }
    }
    
    // Throttle function to limit execution of lazy loading
    function throttle(callback, limit) {
      let waiting = false;
      return function() {
        if (!waiting) {
          callback.apply(this, arguments);
          waiting = true;
          setTimeout(function() {
            waiting = false;
          }, limit);
        }
      };
    }
    
    const throttledLazyLoad = throttle(lazyLoadImages, 200);
    
    window.addEventListener('scroll', throttledLazyLoad);
    window.addEventListener('resize', throttledLazyLoad);
    document.addEventListener('DOMContentLoaded', throttledLazyLoad);
    
    // Initial load
    lazyLoadImages();
  }
  
  // Add low-quality image placeholders for important images
  function generateLQIP() {
    document.querySelectorAll('.lqip-placeholder').forEach(function(placeholder) {
      const img = placeholder.querySelector('img');
      
      if (img && img.dataset.src) {
        // Create a low-quality placeholder if none exists
        if (!placeholder.querySelector('.lqip-blur')) {
          const placeholderDiv = document.createElement('div');
          placeholderDiv.className = 'lqip-blur';
          placeholderDiv.style.backgroundImage = `url(${img.dataset.placeholder || img.src})`;
          placeholder.insertBefore(placeholderDiv, img);
        }
      }
    });
  }
  
  generateLQIP();
  
  // Detect connection speed and adjust accordingly
  function detectConnectionSpeed() {
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    let isSlowConnection = false;
    
    if (connection) {
      // Check if the connection is 2G or the effective type is 2G or slower
      if (connection.type === 'cellular' && connection.effectiveType && 
          (connection.effectiveType === '2g' || connection.effectiveType === 'slow-2g')) {
        isSlowConnection = true;
      }
      // Or if the downlink is very low (less than 0.5 Mbps)
      if (connection.downlink && connection.downlink < 0.5) {
        isSlowConnection = true;
      }
    }
    
    // Add a class to the body for CSS targeting
    if (isSlowConnection) {
      document.body.classList.add('slow-connection');
    }
    
    return isSlowConnection;
  }
  
  // Detect connection speed and apply optimizations
  const isSlowConnection = detectConnectionSpeed();
  
  // For slow connections, preload critical resources and disable animations
  if (isSlowConnection) {
    // Disable non-essential animations
    document.body.classList.add('reduce-motion');
    
    // Adjust quality of images dynamically
    document.querySelectorAll('img[data-quality]').forEach(function(img) {
      if (img.dataset.lowQualitySrc) {
        if (img.dataset.src) {
          img.dataset.src = img.dataset.lowQualitySrc;
        } else {
          img.src = img.dataset.lowQualitySrc;
        }
      }
    });
  }
}); 