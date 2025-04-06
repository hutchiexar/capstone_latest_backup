// Initialize Bootstrap tabs
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltips = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltips.map(function (tooltip) {
        return new bootstrap.Tooltip(tooltip)
    });

    // Handle tab switching
    var triggerTabList = [].slice.call(document.querySelectorAll('#operatorTabs button'))
    triggerTabList.forEach(function (triggerEl) {
        var tabTrigger = new bootstrap.Tab(triggerEl)
        triggerEl.addEventListener('click', function (event) {
            event.preventDefault()
            tabTrigger.show()
        })
    });

    // Highlight unassigned vehicles tab if there are any
    const unassignedCount = document.querySelector('.stat-card-value').textContent;
    if (parseInt(unassignedCount) > 0) {
        document.querySelector('#unassigned-tab').classList.add('attention');
    }
});

// Add animation when switching tabs
document.querySelectorAll('.nav-link').forEach(tab => {
    tab.addEventListener('shown.bs.tab', e => {
        const target = document.querySelector(e.target.getAttribute('data-bs-target'));
        target.classList.add('fade-in');
        setTimeout(() => target.classList.remove('fade-in'), 300);
    });
}); 