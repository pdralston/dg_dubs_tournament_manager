  document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('playerSearchInput');
    
    searchInput.addEventListener('keyup', function() {
      const searchTerm = searchInput.value.toLowerCase();
      const playerRows = document.querySelectorAll('table tbody tr');
      
      playerRows.forEach(function(row) {
        const playerName = row.querySelector('td:first-child').textContent.toLowerCase();
        
        if (playerName.includes(searchTerm)) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  });
