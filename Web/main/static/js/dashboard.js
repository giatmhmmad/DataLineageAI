// Dashboard JavaScript Functions

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    initSidebar();
    initNavigation();
    
    console.log('Dashboard initialized successfully');
});

// Sidebar functionality
function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.querySelector('.sidebar-toggle');
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768) {
            const sidebar = document.querySelector('.sidebar');
            const toggleBtn = document.querySelector('.sidebar-toggle');
            
            if (!sidebar.contains(event.target) && !toggleBtn.contains(event.target)) {
                sidebar.classList.remove('open');
            }
        }
    });
}

// Navigation functionality
function initNavigation() {
    // Set active nav item based on current URL
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (currentPath === href || (currentPath === '/' && href === '/')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Utility functions
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading">Loading...</div>';
    }
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
    }
}

function showEmptyState(elementId, title, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="empty-state">
                <h3>${title}</h3>
                <p>${message}</p>
            </div>
        `;
    }
}

// Table functionality
function initDataTable(tableId) {
    // Add sorting functionality if needed
    const table = document.getElementById(tableId);
    if (table) {
        const headers = table.querySelectorAll('th');
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                // Add sorting logic here
                console.log('Sorting by:', header.textContent);
            });
        });
    }
}

// Data visualization placeholder functions
function initDataLineage() {
    console.log('Initializing data lineage visualization...');
    // This will be implemented when adding actual data lineage features
}

function initCharts() {
    console.log('Initializing charts...');
    // This will be implemented when adding chart libraries
}
