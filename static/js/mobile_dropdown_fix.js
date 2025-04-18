/**
 * Mobile dropdown fixes for Educational Materials menu
 */
document.addEventListener('DOMContentLoaded', function() {
    // Only apply these fixes on mobile devices
    if (window.innerWidth < 992) {
        // Get the educational materials dropdown
        const educationDropdown = document.getElementById('educationDropdown');
        
        if (educationDropdown) {
            // Get the dropdown menu element
            const dropdownMenu = educationDropdown.nextElementSibling;
            
            if (dropdownMenu) {
                // Add class to make it mobile-friendly
                dropdownMenu.classList.add('mobile-friendly-dropdown');
                
                // Adjust position to ensure proper display
                educationDropdown.addEventListener('click', function(e) {
                    // Toggle a class to help with styling
                    dropdownMenu.classList.toggle('dropdown-expanded');
                    
                    // Prevent any weird behavior with nested dropdowns
                    e.stopPropagation();
                });
            }
        }
        
        // Fix for all dropdowns in the navbar
        document.querySelectorAll('.navbar-nav .dropdown-toggle').forEach(function(dropdown) {
            dropdown.addEventListener('click', function(e) {
                // Toggle a mobile-specific class
                this.classList.toggle('mobile-dropdown-active');
                
                // Get the dropdown menu
                const menu = this.nextElementSibling;
                if (menu && menu.classList.contains('dropdown-menu')) {
                    // Add a special class for mobile styling
                    menu.classList.add('mobile-dropdown-menu');
                }
            });
        });
    }
}); 