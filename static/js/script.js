/**
 * Google Search Scraper - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Theme Toggle Functionality
    const themeToggleBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    const darkIconElement = document.querySelector('.theme-icon-dark');
    const lightIconElement = document.querySelector('.theme-icon-light');
    const darkTextElement = document.querySelector('.theme-text-dark');
    const lightTextElement = document.querySelector('.theme-text-light');
    const bootstrapCssLink = document.getElementById('bootstrap-css');

    // Initialize Research Mode toggle style based on current theme
    const currentTheme = htmlElement.getAttribute('data-bs-theme') || 'light';
    if (currentTheme === 'dark') {
        document.querySelectorAll('.form-check-input[type="checkbox"]#research-mode').forEach(toggle => {
            toggle.classList.add('dark-mode-toggle');
        });
    }

    // Check for user's theme preference in local storage or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    // Handle theme toggle button click
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function() {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // Function to apply the theme
    function applyTheme(theme) {
        htmlElement.setAttribute('data-bs-theme', theme);

        // Update button appearance
        if (theme === 'dark') {
            // Show dark mode icons/text, hide light mode ones
            if (darkIconElement) darkIconElement.classList.remove('d-none');
            if (lightIconElement) lightIconElement.classList.add('d-none');
            if (darkTextElement) darkTextElement.classList.remove('d-none');
            if (lightTextElement) lightTextElement.classList.add('d-none');

            // Change theme toggle button style for dark mode
            if (themeToggleBtn) {
                themeToggleBtn.classList.remove('btn-outline-dark');
                themeToggleBtn.classList.add('btn-outline-light');
            }

            // Update Research Mode toggle appearance for dark mode
            document.querySelectorAll('.form-check-input[type="checkbox"]#research-mode').forEach(toggle => {
                toggle.classList.add('dark-mode-toggle');
            });

            // Update all outline-light buttons
            document.querySelectorAll('.btn-outline-light').forEach(btn => {
                if (btn.classList.contains('btn-outline-dark')) {
                    btn.classList.remove('btn-outline-dark');
                }
                if (!btn.classList.contains('btn-outline-light')) {
                    btn.classList.add('btn-outline-light');
                }
            });

            // Change Bootstrap CSS to dark theme
            if (bootstrapCssLink) {
                bootstrapCssLink.href = "https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css";
            }

            // Change header and footer colors
            const header = document.querySelector('header');
            const footer = document.querySelector('footer');
            if (header) {
                header.classList.remove('bg-light');
                header.classList.add('bg-dark');
            }
            if (footer) {
                footer.classList.remove('bg-light');
                footer.classList.add('bg-dark');
            }
        } else {
            // Show light mode icons/text, hide dark mode ones
            if (darkIconElement) darkIconElement.classList.add('d-none');
            if (lightIconElement) lightIconElement.classList.remove('d-none');
            if (darkTextElement) darkTextElement.classList.add('d-none');
            if (lightTextElement) lightTextElement.classList.remove('d-none');

            // Change theme toggle button style for light mode
            if (themeToggleBtn) {
                themeToggleBtn.classList.remove('btn-outline-light');
                themeToggleBtn.classList.add('btn-outline-dark');
            }

            // Update Research Mode toggle appearance for light mode
            document.querySelectorAll('.form-check-input[type="checkbox"]#research-mode').forEach(toggle => {
                toggle.classList.remove('dark-mode-toggle');
            });

            // Update all button colors for light mode
            // Note: We don't change the classes as our CSS handles this with the data-bs-theme attribute

            // Change Bootstrap CSS to light theme
            if (bootstrapCssLink) {
                bootstrapCssLink.href = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css";
            }

            // Change header and footer colors
            const header = document.querySelector('header');
            const footer = document.querySelector('footer');
            if (header) {
                header.classList.remove('bg-dark');
                header.classList.add('bg-light');
            }
            if (footer) {
                footer.classList.remove('bg-dark');
                footer.classList.add('bg-light');
            }
        }
    }

    // Search form validation
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-query');
    const searchButton = document.getElementById('search-button');

    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            if (searchInput.value.trim() === '') {
                e.preventDefault();
                showAlert('Please enter a search query', 'warning');
                searchInput.focus();
            } else {
                // Show loading state
                searchButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Searching...';
                searchButton.disabled = true;
            }
        });
    }

    // Automatically dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add smooth scrolling for internal links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                document.querySelector(targetId).scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

/**
 * Show a bootstrap alert message
 * @param {string} message - Alert message text
 * @param {string} type - Alert type (primary, secondary, success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    const alertsContainer = document.createElement('div');
    alertsContainer.className = 'alert-container';
    alertsContainer.style.position = 'fixed';
    alertsContainer.style.top = '20px';
    alertsContainer.style.right = '20px';
    alertsContainer.style.zIndex = '9999';

    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type} alert-dismissible fade show`;
    alertElement.role = 'alert';
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    alertsContainer.appendChild(alertElement);
    document.body.appendChild(alertsContainer);

    // Auto remove after 5 seconds
    setTimeout(() => {
        alertElement.classList.remove('show');
        setTimeout(() => {
            alertsContainer.remove();
        }, 200);
    }, 5000);
}

// Function to display suggestions in the UI
        function displaySuggestions(suggestions) {
            const suggestionsList = document.getElementById('suggestions-list');
            const suggestionsContainer = document.getElementById('suggestions-container');
            const searchInput = document.getElementById('search-query');
            
            if (!suggestionsList || !suggestionsContainer || !searchInput) return;
            
            // Clear previous suggestions
            suggestionsList.innerHTML = '';

            // Take only first 3 suggestions
            suggestions.slice(0, 3).forEach(suggestion => {
                const button = document.createElement('button');
                button.className = 'btn btn-outline-primary me-2 mb-2'; // Added margin bottom
                button.type = 'button';

                // Add suggestion type icon
                let typeIcon = 'fa-lightbulb';
                if (suggestion.type === 'operator') {
                    typeIcon = 'fa-code';
                } else if (suggestion.type === 'expanded') {
                    typeIcon = 'fa-plus-circle';
                }

                button.innerHTML = `
                    <i class="fas ${typeIcon} me-2"></i>
                    ${suggestion.query}
                `;

                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    searchInput.value = suggestion.query;
                    searchInput.focus();
                });

                suggestionsList.appendChild(button);
            });
            
            // Show suggestions container if we have suggestions
            if (suggestionsList.children.length > 0) {
                suggestionsContainer.classList.remove('d-none');
            }
}
}