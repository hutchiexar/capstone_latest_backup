/**
 * JavaScript functionality for the Adjudication History page
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize any interactive components
    
    // Add search functionality to the table
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('.table tbody tr');
            
            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }
    
    // Initialize any tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (tooltipTriggerList.length > 0) {
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Handle tab navigation in the detail view
    const detailTabs = document.querySelectorAll('.adjudication-detail-tab');
    if (detailTabs.length > 0) {
        detailTabs.forEach(tab => {
            tab.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Remove active class from all tabs
                detailTabs.forEach(t => {
                    t.classList.remove('active');
                    const target = document.querySelector(t.getAttribute('data-bs-target'));
                    if (target) target.classList.remove('show', 'active');
                });
                
                // Add active class to clicked tab
                this.classList.add('active');
                const target = document.querySelector(this.getAttribute('data-bs-target'));
                if (target) target.classList.add('show', 'active');
            });
        });
    }
    
    // Handle export button actions
    const exportButtons = document.querySelectorAll('.export-btn');
    if (exportButtons.length > 0) {
        exportButtons.forEach(button => {
            button.addEventListener('click', function() {
                const format = this.getAttribute('data-format');
                // Any additional export logic can go here
                console.log(`Exporting in ${format} format`);
            });
        });
    }
    
    // Handle filter form submission
    const filterForm = document.getElementById('adjudication-filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            // Any additional filter logic can go here
            console.log('Applying filters');
        });
    }
}); 