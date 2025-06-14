/**
 * team_generator.js - Handles functionality for the generate teams page
 */
document.addEventListener('DOMContentLoaded', function() {
    // Add functionality for the player selection form
    const playerForm = document.getElementById('player-selection-form');
    if (!playerForm) return;
    
    // Handle select/deselect all functionality
    const selectAllBtn = document.getElementById('select-all');
    const deselectAllBtn = document.getElementById('deselect-all');
    const playerCheckboxes = document.querySelectorAll('input[name="players"]');
    
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function(e) {
            e.preventDefault();
            playerCheckboxes.forEach(checkbox => {
                checkbox.checked = true;
            });
        });
    }
    
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function(e) {
            e.preventDefault();
            playerCheckboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
        });
    }
    
    // Validate form submission
    if (playerForm) {
        playerForm.addEventListener('submit', function(e) {
            const selectedPlayers = document.querySelectorAll('input[name="players"]:checked');
            if (selectedPlayers.length < 2) {
                e.preventDefault();
                alert('Please select at least 2 players');
            }
        });
    }
});
