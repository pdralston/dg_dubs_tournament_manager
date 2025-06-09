// Common JavaScript functionality for the Disc Golf League Rating System

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 5000);
    });
    
    // Add responsive table support
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        if (!table.classList.contains('responsive-table')) {
            table.classList.add('responsive-table');
            
            // Get all headers
            const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
            
            // Add data attributes to each cell for mobile view
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                cells.forEach((cell, index) => {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index]);
                    }
                });
            });
        }
    });
});
