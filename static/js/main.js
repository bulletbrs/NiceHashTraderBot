/**
 * NiceHash Order Manager - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Format timestamps
    const formatDates = () => {
        document.querySelectorAll('.timestamp').forEach(element => {
            const timestamp = element.textContent;
            if (timestamp && timestamp !== '') {
                try {
                    const date = new Date(timestamp);
                    element.textContent = date.toLocaleString();
                } catch (error) {
                    console.error('Error formatting date:', error);
                }
            }
        });
    };

    // Format numbers to display fixed decimal places
    const formatNumbers = () => {
        document.querySelectorAll('.number-format').forEach(element => {
            const value = parseFloat(element.textContent);
            const decimals = element.dataset.decimals || 8;
            if (!isNaN(value)) {
                element.textContent = value.toFixed(decimals);
            }
        });
    };

    // Handle order refill modal
    const setupRefillModal = () => {
        const refillModal = document.getElementById('refillModal');
        if (refillModal) {
            refillModal.addEventListener('show.bs.modal', function(event) {
                const button = event.relatedTarget;
                const orderId = button.getAttribute('data-order-id');
                const availableAmount = button.getAttribute('data-available-amount');
                
                const modalTitle = refillModal.querySelector('.modal-title');
                const orderIdField = refillModal.querySelector('#orderId');
                const availableAmountField = refillModal.querySelector('#availableAmount');
                
                modalTitle.textContent = `Refill Order ${orderId.substring(0, 8)}...`;
                orderIdField.value = orderId;
                availableAmountField.textContent = availableAmount;
            });
        }
    };

    // Setup interval refresh for active pages
    const setupAutoRefresh = () => {
        const refreshIntervalMinutes = 2; // Refresh every 2 minutes
        const pathsToRefresh = ['/orders', '/'];
        
        if (pathsToRefresh.includes(window.location.pathname)) {
            setTimeout(() => {
                window.location.reload();
            }, refreshIntervalMinutes * 60 * 1000);
        }
    };

    // Initialize tooltips
    const initTooltips = () => {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    };

    // Run initializations
    formatDates();
    formatNumbers();
    setupRefillModal();
    setupAutoRefresh();
    initTooltips();

    // Handle form submission with confirmation
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = this.getAttribute('data-confirm');
            
            if (confirm(message)) {
                this.submit();
            }
        });
    });
});

// Function to update server time display
function updateServerTime(timestamp) {
    const serverTimeElement = document.getElementById('serverTime');
    if (serverTimeElement) {
        const serverDate = new Date(parseInt(timestamp));
        serverTimeElement.textContent = serverDate.toLocaleTimeString();
    }
}

// Function to handle error responses
function handleApiError(error, elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle me-2"></i>
                Error: ${error}
            </div>
        `;
    }
    console.error('API Error:', error);
}

// Function to show loading indicator
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="d-flex justify-content-center my-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }
}
