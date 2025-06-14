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
    
    // Track all autocomplete instances
    const autocompleteInstances = [];
    
    // Initialize existing player inputs
    initializeExistingInputs();
    
    // Add team button functionality
    const addTeamButton = document.getElementById('add-team');
    if (addTeamButton) {
        addTeamButton.addEventListener('click', function() {
            addNewTeamRow(teamCount, playersData);
            teamCount++;
            updatePositionNumbers();
        });
    }
    
    // Form validation
    const tournamentForm = document.querySelector('form');
    if (tournamentForm) {
        tournamentForm.addEventListener('submit', function(e) {
            // Validate all inputs first
            let allValid = true;
            autocompleteInstances.forEach(instance => {
                if (!instance.validateInput(true)) {
                    allValid = false;
                }
            });
            
            if (!allValid) {
                e.preventDefault();
                const errorMsg = document.getElementById('validation-error');
                if (errorMsg) {
                    errorMsg.textContent = 'Please correct the invalid player names.';
                    errorMsg.style.display = 'block';
                }
                return;
            }
            
            // Count valid teams (teams with both players and a score)
            let validTeams = 0;
            const teamRows = document.querySelectorAll('.team-result');
            
            teamRows.forEach(row => {
                const player1Input = row.querySelector('input[name^="player1_"]');
                const player2Input = row.querySelector('input[name^="player2_"]');
                const scoreInput = row.querySelector('input[name^="score_"]');
                
                if (player1Input && player2Input && scoreInput && 
                    player1Input.value.trim() && player2Input.value.trim() && scoreInput.value.trim()) {
                    validTeams++;
                }
            });
            
            // Check if we have at least 2 valid teams
            if (validTeams < 2) {
                e.preventDefault();
                
                // Show error message
                const errorMsg = document.getElementById('validation-error');
                if (errorMsg) {
                    errorMsg.textContent = 'At least 2 complete teams are required to record a tournament.';
                    errorMsg.style.display = 'block';
                    
                    // Scroll to error message
                    errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    alert('At least 2 complete teams are required to record a tournament.');
                }
            }
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
     * Initialize autocomplete for existing player inputs
     */
    function initializeExistingInputs() {
        const existingRows = document.querySelectorAll('.team-result');
        existingRows.forEach(row => {
            const player1Input = row.querySelector('input[name^="player1_"]');
            const player2Input = row.querySelector('input[name^="player2_"]');
            
            if (player1Input) {
                const autocomplete1 = new PlayerAutocomplete(player1Input, playersData);
                autocompleteInstances.push(autocomplete1);
            }
            
            if (player2Input) {
                const autocomplete2 = new PlayerAutocomplete(player2Input, playersData);
                autocompleteInstances.push(autocomplete2);
            }
            
            // Add remove button functionality
            const removeButton = row.querySelector('.remove-team');
            if (removeButton) {
                removeButton.addEventListener('click', function() {
                    row.remove();
                    updatePositionNumbers();
                });
            }
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
        teamDiv.dataset.index = index;
        
        const position = document.createElement('div');
        position.className = 'position';
        position.textContent = index + 1;
        
        const inputs = document.createElement('div');
        inputs.className = 'team-inputs';
        
        // Create player 1 input wrapper
        const player1Wrapper = document.createElement('div');
        player1Wrapper.className = 'player-input';
        
        // Create player 1 input
        const player1Input = document.createElement('input');
        player1Input.type = 'text';
        player1Input.name = `player1_${index}`;
        player1Input.placeholder = 'Player 1';
        player1Input.required = true;
        player1Wrapper.appendChild(player1Input);
        
        // Create player 2 input wrapper
        const player2Wrapper = document.createElement('div');
        player2Wrapper.className = 'player-input';
        
        // Create player 2 input
        const player2Input = document.createElement('input');
        player2Input.type = 'text';
        player2Input.name = `player2_${index}`;
        player2Input.placeholder = 'Player 2';
        player2Input.required = true;
        player2Wrapper.appendChild(player2Input);
        
        // Create score input wrapper
        const scoreWrapper = document.createElement('div');
        scoreWrapper.className = 'score-input';
        
        // Create score input
        const scoreInput = document.createElement('input');
        scoreInput.type = 'number';
        scoreInput.name = `score_${index}`;
        scoreInput.placeholder = 'Score';
        scoreInput.required = true;
        scoreWrapper.appendChild(scoreInput);
        
        // Create remove button
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'remove-team';
        removeButton.innerHTML = '&times;';
        removeButton.title = 'Remove Team';
        removeButton.addEventListener('click', function() {
            teamDiv.remove();
            updatePositionNumbers();
        });
        
        // Add all elements to the DOM
        inputs.appendChild(player1Wrapper);
        inputs.appendChild(player2Wrapper);
        inputs.appendChild(scoreWrapper);
        inputs.appendChild(removeButton);
        
        teamDiv.appendChild(position);
        teamDiv.appendChild(inputs);
        
        teamResultsContainer.appendChild(teamDiv);
        
        // Initialize autocomplete for player inputs
        const autocomplete1 = new PlayerAutocomplete(player1Input, players);
        const autocomplete2 = new PlayerAutocomplete(player2Input, players);
        
        autocompleteInstances.push(autocomplete1, autocomplete2);
        
        // Set values if team data is provided
        if (teamData) {
            player1Input.value = teamData.player1;
            player2Input.value = teamData.player2;
            
            // Validate the inputs
            autocomplete1.validateInput();
            autocomplete2.validateInput();
        }
    }
    
    /**
     * Updates the position numbers for all team rows
     */
    function updatePositionNumbers() {
        const teamRows = document.querySelectorAll('.team-result');
        teamRows.forEach((row, index) => {
            const position = row.querySelector('.position');
            if (position) {
                position.textContent = index + 1;
            }
        });
    }
});
