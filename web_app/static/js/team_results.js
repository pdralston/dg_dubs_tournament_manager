/**
 * team_results.js - Handles functionality for the team results page
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get the teams data from the data attribute
    const teamsContainer = document.getElementById('teams-data-container');
    if (!teamsContainer) return;
    
    const teamsData = JSON.parse(teamsContainer.dataset.teams || '[]');
    
    // Handle record tournament button click
    const recordTournamentBtn = document.getElementById('record-tournament-btn');
    if (recordTournamentBtn) {
        recordTournamentBtn.addEventListener('click', function() {
            // Convert teams data to JSON string
            const teamsJson = JSON.stringify(teamsData);
            
            // Get the URL from the data attribute
            const recordUrl = teamsContainer.dataset.recordUrl;
            
            // Redirect to record tournament page with teams data
            window.location.href = recordUrl + "?teams=" + encodeURIComponent(teamsJson);
        });
    }
});
