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
    
    // Track tournament participants
    const tournamentParticipants = new Set();
    
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
                    
                    // Add players to tournament participants set
                    if (player1Input.value !== "Ghost Player") {
                        tournamentParticipants.add(player1Input.value);
                    }
                    if (player2Input.value !== "Ghost Player") {
                        tournamentParticipants.add(player2Input.value);
                    }
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
    
    // Ace Pot functionality
    const acePotCheckbox = document.getElementById('ace-pot-paid');
    const acePotRecipients = document.getElementById('ace-pot-recipients');
    const addRecipientBtn = document.getElementById('add-recipient-btn');
    const recipientList = document.querySelector('.ace-pot-recipient-list');
    let recipientCount = 0;
    
    // Show/hide recipients section based on checkbox
    if (acePotCheckbox) {
        acePotCheckbox.addEventListener('change', function() {
            if (this.checked) {
                acePotRecipients.style.display = 'block';
                
                // Add first recipient if none exist
                if (recipientCount === 0) {
                    addAcePotRecipient();
                }
            } else {
                acePotRecipients.style.display = 'none';
            }
        });
    }
    
    // Add recipient button
    if (addRecipientBtn) {
        addRecipientBtn.addEventListener('click', function() {
            addAcePotRecipient();
        });
    }
    
    /**
     * Add a new ace pot recipient input
     */
    function addAcePotRecipient() {
        const recipientDiv = document.createElement('div');
        recipientDiv.className = 'ace-pot-recipient';
        recipientDiv.style.display = 'flex';
        recipientDiv.style.alignItems = 'center';
        recipientDiv.style.marginBottom = '10px';
        recipientDiv.style.gap = '10px';
        
        // Create autocomplete wrapper
        const autocompleteWrapper = document.createElement('div');
        autocompleteWrapper.className = 'autocomplete-wrapper';
        autocompleteWrapper.style.flex = '1';
        
        // Create input
        const input = document.createElement('input');
        input.type = 'text';
        input.name = `ace_pot_recipient_${recipientCount}`;
        input.placeholder = 'Select player';
        input.required = acePotCheckbox.checked;
        autocompleteWrapper.appendChild(input);
        
        // Create remove button
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'remove-recipient';
        removeBtn.innerHTML = '&times;';
        removeBtn.title = 'Remove Recipient';
        removeBtn.style.backgroundColor = '#ff4d4d';
        removeBtn.style.color = 'white';
        removeBtn.style.border = 'none';
        removeBtn.style.borderRadius = '50%';
        removeBtn.style.width = '24px';
        removeBtn.style.height = '24px';
        removeBtn.style.fontSize = '16px';
        removeBtn.style.cursor = 'pointer';
        removeBtn.style.display = 'flex';
        removeBtn.style.alignItems = 'center';
        removeBtn.style.justifyContent = 'center';
        removeBtn.style.padding = '0';
        
        removeBtn.addEventListener('click', function() {
            recipientDiv.remove();
            updateRecipientCount();
        });
        
        recipientDiv.appendChild(autocompleteWrapper);
        recipientDiv.appendChild(removeBtn);
        recipientList.appendChild(recipientDiv);
        
        // Initialize autocomplete for this input
        // Use tournament participants instead of all players
        const autocomplete = new PlayerAutocomplete(input, Array.from(tournamentParticipants));
        autocompleteInstances.push(autocomplete);
        
        recipientCount++;
        updateRecipientCount();
    }
    
    /**
     * Update recipient count and required status
     */
    function updateRecipientCount() {
        const recipients = document.querySelectorAll('.ace-pot-recipient');
        recipientCount = recipients.length;
        
        // If no recipients and checkbox is checked, add one
        if (recipientCount === 0 && acePotCheckbox.checked) {
            addAcePotRecipient();
        }
        
        // Update required status based on checkbox
        recipients.forEach(recipient => {
            const input = recipient.querySelector('input');
            if (input) {
                input.required = acePotCheckbox.checked;
            }
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
                
                // Add input event to track tournament participants
                player1Input.addEventListener('change', updateTournamentParticipants);
            }
            
            if (player2Input) {
                const autocomplete2 = new PlayerAutocomplete(player2Input, playersData);
                autocompleteInstances.push(autocomplete2);
                
                // Add input event to track tournament participants
                player2Input.addEventListener('change', updateTournamentParticipants);
            }
            
            // Add remove button functionality
            const removeButton = row.querySelector('.remove-team');
            if (removeButton) {
                removeButton.addEventListener('click', function() {
                    row.remove();
                    updatePositionNumbers();
                    updateTournamentParticipants();
                });
            }
        });
        
        // Initial update of tournament participants
        updateTournamentParticipants();
    }
    
    /**
     * Update the set of tournament participants
     */
    function updateTournamentParticipants() {
        tournamentParticipants.clear();
        
        const teamRows = document.querySelectorAll('.team-result');
        teamRows.forEach(row => {
            const player1Input = row.querySelector('input[name^="player1_"]');
            const player2Input = row.querySelector('input[name^="player2_"]');
            
            if (player1Input && player1Input.value && player1Input.value !== "Ghost Player") {
                tournamentParticipants.add(player1Input.value);
            }
            
            if (player2Input && player2Input.value && player2Input.value !== "Ghost Player") {
                tournamentParticipants.add(player2Input.value);
            }
        });
        
        // Update recipient autocomplete options
        const recipientInputs = document.querySelectorAll('.ace-pot-recipient input');
        recipientInputs.forEach(input => {
            const instance = autocompleteInstances.find(i => i.input === input);
            if (instance) {
                instance.updateOptions(Array.from(tournamentParticipants));
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
            updateTournamentParticipants();
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
        
        // Add input event to track tournament participants
        player1Input.addEventListener('change', updateTournamentParticipants);
        player2Input.addEventListener('change', updateTournamentParticipants);
        
        // Set values if team data is provided
        if (teamData) {
            player1Input.value = teamData.player1;
            player2Input.value = teamData.player2;
            
            // Validate the inputs
            autocomplete1.validateInput();
            autocomplete2.validateInput();
            
            // Update tournament participants
            updateTournamentParticipants();
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
