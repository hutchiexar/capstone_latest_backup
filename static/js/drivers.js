// Lazy loading implementation
let loading = false;
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting && !loading && {{ drivers.has_next|yesno:"true,false" }}) {
      loadMoreDrivers({{ drivers.next_page_number }});
    }
  });
}, { threshold: 0.5 });

// Upload progress handling
document.querySelector('a[href="{% url 'driver_import' %}"]').addEventListener('click', (e) => {
  e.preventDefault();
  const overlay = document.createElement('div');
  overlay.className = 'loading-overlay';
  overlay.innerHTML = `
    <div class="text-center">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="mt-2">Processing your file...</p>
      <div class="progress mt-2" style="width: 200px">
        <div class="upload-progress"></div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  
  // Implement actual file upload logic with progress tracking
  // ...
});

// Load more drivers function
function loadMoreDrivers(page) {
  loading = true;
  fetch(`?page=${page}&partial=1`)
    .then(response => response.text())
    .then(html => {
      const temp = document.createElement('div');
      temp.innerHTML = html;
      const newItems = temp.querySelectorAll('.driver-item');
      newItems.forEach(item => {
        document.getElementById('driver-list').appendChild(item);
        observer.observe(item);
      });
      loading = false;
    });
}

// Initial observation
document.querySelectorAll('.driver-item').forEach(item => {
  observer.observe(item);
});

/* Hover effects */
.btn {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* Focus states */
.btn:focus {
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.3);
}

/* Responsive table */
@media (max-width: 768px) {
  .table-responsive {
    border: 0;
  }
  
  .table thead {
    clip: rect(0 0 0 0);
    height: 1px;
    margin: -1px;
    overflow: hidden;
    padding: 0;
    position: absolute;
    width: 1px;
  }
  
  .table tr {
    display: block;
    margin-bottom: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  
  .table td {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    font-size: 0.9em;
    text-align: right;
  }
  
  .table td::before {
    content: attr(data-label);
    float: left;
    font-weight: 600;
    text-transform: uppercase;
    color: #666;
  }
} 