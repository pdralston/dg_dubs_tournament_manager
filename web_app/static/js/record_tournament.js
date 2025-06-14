/**
 * record_tournament.js - Handles functionality for the record tournament page
 */
document.addEventListener('DOMContentLoaded', function() {
    const teamResultsContainer = document.getElementById('team-results');
    if (!teamResultsContainer) return;
    
    // Get data from the container
    const playersData = JSON.parse(teamResultsContainer.dataset.players || '[]');
    const prePopulatedTeams = JSON.parse(teamResultsContainer.dataset.prePopulatedTeams || '[]');
    let teamCount = parseInt(teamResultsContainer.dataset.initialTeamCount || 5);
    
    // Add team button functionality
    const addTeamButton = document.getElementById('add-team');
    if (addTeamButton) {
        addTeamButton.addEventListener('click', function() {
            addNewTeamRow(teamCount, playersData);
            teamCount++;
        });
    }
    
    // Pre-populate teams if available
    if (prePopulatedTeams.length > 0) {
        // Clear existing team rows
        teamResultsContainer.innerHTML = '';
        teamCount = 0;
        
        // Add a row for each team
        prePopulatedTeams.forEach((team, index) => {
            addNewTeamRow(index, playersData, team);
            teamCount++;
        });
    }
    
    /**
     * Adds a new team row to the form
     * @param {number} index - The team index
     * @param {Array} players - List of player names
     * @param {Object} teamData - Optional team data for pre-populating
     */
    function addNewTeamRow(index, players, teamData = null) {
        const teamDiv = document.createElement('div');
        teamDiv.className = 'team-result';
        
        const position = document.createElement('div');
        position.className = 'position';
        position.textContent = index + 1;
        
        const inputs = document.createElement('div');
        inputs.className = 'team-inputs';
        
        // Create player 1 select
        const player1Select = document.createElement('select');
        player1Select.name = `player1_${index}`;
        player1Select.required = true;
        
        let player1Options = '<option value="">-- Select Player 1 --</option>';
        players.forEach(player => {
            player1Options += `<option value="${player}">${player}</option>`;
        });
        player1Options += '<option value="Ghost Player">Ghost Player</option>';
        player1Select.innerHTML = player1Options;
        
        // Create player 2 select
        const player2Select = document.createElement('select');
        player2Select.name = `player2_${index}`;
        player2Select.required = true;
        
        let player2Options = '<option value="">-- Select Player 2 --</option>';
        players.forEach(player => {
            player2Options += `<option value="${player}">${player}</option>`;
        });
        player2Options += '<option value="Ghost Player">Ghost Player</option>';
        player2Select.innerHTML = player2Options;
        
        // Create score input
        const scoreInput = document.createElement('input');
        scoreInput.type = 'number';
        scoreInput.name = `score_${index}`;
        scoreInput.placeholder = 'Score';
        scoreInput.required = true;
        
        // Add all elements to the DOM
        inputs.appendChild(player1Select);
        inputs.appendChild(player2Select);
        inputs.appendChild(scoreInput);
        
        teamDiv.appendChild(position);
        teamDiv.appendChild(inputs);
        
        teamResultsContainer.appendChild(teamDiv);
        
        // Set selected values if team data is provided
        if (teamData) {
            player1Select.value = teamData.player1;
            player2Select.value = teamData.player2;
        }
    }
});
