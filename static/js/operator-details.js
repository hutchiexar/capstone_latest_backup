/**
 * Operator Details Functionality
 * Handles loading and displaying operator details in a modal
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add event listeners to all detail buttons
    document.querySelectorAll('.operator-detail-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const operatorId = this.getAttribute('data-operator-id');
            loadOperatorDetails(operatorId);
        });
    });
});

/**
 * Load operator details and show in modal
 * @param {number} operatorId - The ID of the operator to load
 */
function loadOperatorDetails(operatorId) {
    // Get modal element
    const modal = document.getElementById('operatorDetailsModal');
    const modalBody = modal.querySelector('.modal-body');
    
    // Show modal with loading spinner
    modalBody.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 mb-0">Loading operator details...</p>
        </div>
    `;
    
    // Show the modal
    const operatorModal = new bootstrap.Modal(modal);
    operatorModal.show();
    
    // Fetch operator details via AJAX
    fetch(`/operators/${operatorId}/details-json/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Create content for the modal
            let modalContent = `
            <div class="row">
                <!-- Operator Personal Info -->
                <div class="col-md-6">
                    <div class="card shadow-sm border-0 rounded-3 mb-3">
                        <div class="card-header bg-transparent d-flex align-items-center px-4 py-3 border-bottom">
                            <span class="material-icons me-2" style="color: var(--primary-color); font-size: 24px;">person</span>
                            <h5 class="mb-0 fw-bold">Personal Information</h5>
                        </div>
                        <div class="card-body p-4">
                            <div class="row mb-3">
                                <div class="col-md-4 text-muted">Full Name:</div>
                                <div class="col-md-8 fw-medium">${data.operator.first_name} ${data.operator.middle_initial ? data.operator.middle_initial : ''} ${data.operator.last_name}</div>
                            </div>
                            <div class="row mb-3">
                                <div class="col-md-4 text-muted">Address:</div>
                                <div class="col-md-8">${data.operator.address}</div>
                            </div>
                            <div class="row mb-3">
                                <div class="col-md-4 text-muted">Old P.D. Number:</div>
                                <div class="col-md-8">${data.operator.old_pd_number || 'None'}</div>
                            </div>
                            <div class="row mb-3">
                                <div class="col-md-4 text-muted">New P.D. Number:</div>
                                <div class="col-md-8">${data.operator.new_pd_number}</div>
                            </div>
                            <div class="row">
                                <div class="col-md-4 text-muted">Registration Date:</div>
                                <div class="col-md-8">${data.operator.created_at}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Operator Vehicles/P.O. Numbers -->
                <div class="col-md-6">
                    <div class="card shadow-sm border-0 rounded-3">
                        <div class="card-header bg-transparent d-flex align-items-center px-4 py-3 border-bottom">
                            <span class="material-icons me-2" style="color: var(--primary-color); font-size: 24px;">directions_car</span>
                            <h5 class="mb-0 fw-bold">P.O. Numbers</h5>
                        </div>
                        <div class="card-body p-4">`;
            
            if (data.vehicles && data.vehicles.length > 0) {
                modalContent += `
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="border-top-0 px-4 py-3 fw-semibold">Old P.D. Number</th>
                                    <th class="border-top-0 px-4 py-3 fw-semibold">New P.D. Number</th>
                                </tr>
                            </thead>
                            <tbody>`;
                
                // Add each vehicle to the table
                data.vehicles.forEach(function(vehicle) {
                    modalContent += `
                        <tr>
                            <td class="px-4 py-3">${vehicle.old_pd_number || 'None'}</td>
                            <td class="fw-medium px-4 py-3">${vehicle.new_pd_number}</td>
                        </tr>`;
                });
                
                modalContent += `
                            </tbody>
                        </table>
                    </div>`;
            } else {
                modalContent += `
                    <div class="d-flex flex-column align-items-center py-5">
                        <span class="material-icons" style="font-size: 64px; color: #c0c0c0;">directions_car_off</span>
                        <p class="mt-3 mb-0 fs-5">No vehicles associated with this operator.</p>
                        <p class="text-muted mt-2">This operator does not have any registered P.O. numbers yet.</p>
                    </div>`;
            }
            
            modalContent += `
                        </div>
                    </div>
                </div>
            </div>`;
            
            // Update modal content
            modalBody.innerHTML = modalContent;
        })
        .catch(error => {
            // Show error message
            modalBody.innerHTML = `
                <div class="alert alert-danger mb-0">
                    <div class="d-flex align-items-center">
                        <span class="material-icons fs-1 me-3">error_outline</span>
                        <div>
                            <h5 class="alert-heading mb-1">Error Loading Details</h5>
                            <p class="mb-0">Unable to load operator details. Please try again later.</p>
                        </div>
                    </div>
                </div>
            `;
            console.error("Error loading operator details:", error);
        });
} 