/**
 * record_tournament.js - Handles functionality for the record tournament page
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Record Tournament JS loaded');
    
    const teamResultsContainer = document.getElementById('team-results');
    if (!teamResultsContainer) {
        console.error('Team results container not found');
        return;
    }
    
    // Get data from the container with better error handling
    let playersData = [];
    let prePopulatedTeams = [];
    let teamCount = 5;
    
    try {
        // Log raw data for debugging
        console.log('Raw players data:', teamResultsContainer.dataset.players);
        playersData = JSON.parse(teamResultsContainer.dataset.players || '[]');
        console.log('Parsed players data:', playersData);
    } catch (error) {
        console.error('Error parsing players data:', error);
        playersData = [];
    }
    
    try {
        console.log('Raw pre-populated teams data:', teamResultsContainer.dataset.prePopulatedTeams);
        prePopulatedTeams = JSON.parse(teamResultsContainer.dataset.prePopulatedTeams || '[]');
        console.log('Parsed pre-populated teams:', prePopulatedTeams);
    } catch (error) {
        console.error('Error parsing pre-populated teams:', error);
        prePopulatedTeams = [];
    }
    
    try {
        teamCount = parseInt(teamResultsContainer.dataset.initialTeamCount || '5');
        console.log('Team count:', teamCount);
    } catch (error) {
        console.error('Error parsing team count:', error);
        teamCount = 5;
    }
    
    // Create a list of available players
    const availablePlayers = playersData;
    
    // Track tournament participants
    const tournamentParticipants = new Set();
    
    // Initialize player input autocomplete
    initializePlayerInputs();
    
    // Add team button functionality
    const addTeamButton = document.getElementById('add-team');
    if (addTeamButton) {
        addTeamButton.addEventListener('click', function() {
            addNewTeamRow(teamCount);
            teamCount++;
            updatePositionNumbers();
        });
    }
    
    // Form validation
    const tournamentForm = document.querySelector('form');
    if (tournamentForm) {
        tournamentForm.addEventListener('submit', function(e) {
            // Count valid teams (teams with both players and a score)
            let validTeams = 0;
            let invalidPlayerFound = false;
            const teamRows = document.querySelectorAll('.team-result');
            
            teamRows.forEach(row => {
                const player1Input = row.querySelector('input[name^="player1_"]');
                const player2Input = row.querySelector('input[name^="player2_"]');
                const scoreInput = row.querySelector('input[name^="score_"]');
                
                if (player1Input && player2Input && scoreInput && 
                    player1Input.value.trim() && player2Input.value.trim() && scoreInput.value.trim()) {
                    
                    // Validate player names (case-insensitive)
                    const player1Valid = validatePlayerName(player1Input.value);
                    const player2Valid = validatePlayerName(player2Input.value);
                    
                    if (!player1Valid) {
                        console.error('Invalid player name:', player1Input.value);
                        player1Input.classList.add('invalid');
                        invalidPlayerFound = true;
                    } else {
                        player1Input.classList.remove('invalid');
                    }
                    
                    if (!player2Valid) {
                        console.error('Invalid player name:', player2Input.value);
                        player2Input.classList.add('invalid');
                        invalidPlayerFound = true;
                    } else {
                        player2Input.classList.remove('invalid');
                    }
                    
                    if (player1Valid && player2Valid) {
                        validTeams++;
                    }
                }
            });
            
            // Check for invalid players
            if (invalidPlayerFound) {
                e.preventDefault();
                const errorMsg = document.getElementById('validation-error');
                if (errorMsg) {
                    errorMsg.textContent = 'Please correct the invalid player names.';
                    errorMsg.style.display = 'block';
                    errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return;
            }
            
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
    
    /**
     * Validate player name against available players (case-insensitive)
     * @param {string} playerName - The player name to validate
     * @returns {boolean} - Whether the player name is valid
     */
    function validatePlayerName(playerName) {
        if (!playerName) return false;
        
        // Ghost Player is always valid
        if (playerName.trim() === "Ghost Player") return true;
        
        // Case-insensitive check against available players
        return availablePlayers.some(player => 
            player.toLowerCase() === playerName.trim().toLowerCase()
        );
    }
    
    // Pre-populate teams if available
    if (prePopulatedTeams.length > 0) {
        console.log('Pre-populating teams:', prePopulatedTeams);
        
        // Clear existing team rows
        teamResultsContainer.innerHTML = '';
        teamCount = 0;
        
        // Add a row for each team
        prePopulatedTeams.forEach((team, index) => {
            addNewTeamRow(index, team);
            teamCount++;
        });
        
        // Log tournament participants after pre-populating
        console.log("Tournament participants after pre-populating:", Array.from(tournamentParticipants));
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
        
        // Create player input wrapper
        const playerInputWrapper = document.createElement('div');
        playerInputWrapper.className = 'player-input';
        playerInputWrapper.style.flex = '1';
        
        // Create input
        const input = document.createElement('input');
        input.type = 'text';
        input.name = `ace_pot_recipient_${recipientCount}`;
        input.id = `ace_pot_recipient_${recipientCount}`;
        input.placeholder = 'Select player';
        input.required = acePotCheckbox.checked;
        
        // Create autocomplete container
        const autocompleteContainer = document.createElement('div');
        autocompleteContainer.className = 'autocomplete-items';
        autocompleteContainer.id = `autocomplete_ace_pot_recipient_${recipientCount}`;
        
        playerInputWrapper.appendChild(input);
        playerInputWrapper.appendChild(autocompleteContainer);
        
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
        
        recipientDiv.appendChild(playerInputWrapper);
        recipientDiv.appendChild(removeBtn);
        recipientList.appendChild(recipientDiv);
        
        // Initialize autocomplete for this input with tournament participants only
        setupAcePotRecipientAutocomplete(input, autocompleteContainer);
        
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
        if (recipientCount === 0 && acePotCheckbox && acePotCheckbox.checked) {
            addAcePotRecipient();
        }
        
        // Update required status based on checkbox
        recipients.forEach(recipient => {
            const input = recipient.querySelector('input');
            if (input && acePotCheckbox) {
                input.required = acePotCheckbox.checked;
            }
        });
    }
    
    /**
     * Initialize player input autocomplete
     */
    function initializePlayerInputs() {
        // Initialize existing player inputs
        const existingRows = document.querySelectorAll('.team-result');
        existingRows.forEach(row => {
            const player1Input = row.querySelector('input[name^="player1_"]');
            const player2Input = row.querySelector('input[name^="player2_"]');
            
            const autocomplete1 = row.querySelector(`#autocomplete_${player1Input.id}`);
            const autocomplete2 = row.querySelector(`#autocomplete_${player2Input.id}`);
            
            if (player1Input && autocomplete1) {
                setupPlayerAutocomplete(player1Input, autocomplete1);
                
                // Add existing player to participants set
                if (player1Input.value && player1Input.value !== "Ghost Player") {
                    tournamentParticipants.add(player1Input.value);
                    player1Input.dataset.previousValue = player1Input.value;
                }
            }
            
            if (player2Input && autocomplete2) {
                setupPlayerAutocomplete(player2Input, autocomplete2);
                
                // Add existing player to participants set
                if (player2Input.value && player2Input.value !== "Ghost Player") {
                    tournamentParticipants.add(player2Input.value);
                    player2Input.dataset.previousValue = player2Input.value;
                }
            }
            
            // Add remove button functionality
            const removeButton = row.querySelector('.remove-team');
            if (removeButton) {
                removeButton.addEventListener('click', function() {
                    // Remove players from tournament participants
                    if (player1Input.value && player1Input.value !== "Ghost Player") {
                        tournamentParticipants.delete(player1Input.value);
                    }
                    
                    if (player2Input.value && player2Input.value !== "Ghost Player") {
                        tournamentParticipants.delete(player2Input.value);
                    }
                    
                    row.remove();
                    updatePositionNumbers();
                    
                    // Update ace pot recipient inputs
                    updateAcePotRecipientInputs();
                });
            }
            
            // Add change event listeners to update tournament participants
            player1Input.addEventListener('change', function() {
                // Remove old value from participants if it exists
                if (this.dataset.previousValue && this.dataset.previousValue !== "Ghost Player") {
                    tournamentParticipants.delete(this.dataset.previousValue);
                }
                
                // Add new value to participants if it's valid
                if (this.value && this.value !== "Ghost Player" && validatePlayerName(this.value)) {
                    tournamentParticipants.add(this.value);
                }
                
                // Store current value for future reference
                this.dataset.previousValue = this.value;
                
                // Update ace pot recipient inputs
                updateAcePotRecipientInputs();
            });
            
            player2Input.addEventListener('change', function() {
                // Remove old value from participants if it exists
                if (this.dataset.previousValue && this.dataset.previousValue !== "Ghost Player") {
                    tournamentParticipants.delete(this.dataset.previousValue);
                }
                
                // Add new value to participants if it's valid
                if (this.value && this.value !== "Ghost Player" && validatePlayerName(this.value)) {
                    tournamentParticipants.add(this.value);
                }
                
                // Store current value for future reference
                this.dataset.previousValue = this.value;
                
                // Update ace pot recipient inputs
                updateAcePotRecipientInputs();
            });
        });
    }
    
    /**
     * Setup autocomplete for player input
     * @param {HTMLElement} inputElement - The input element
     * @param {HTMLElement} autocompleteContainer - The autocomplete container
     */
    function setupPlayerAutocomplete(inputElement, autocompleteContainer) {
        inputElement.addEventListener('input', function() {
            const searchTerm = this.value.trim().toLowerCase();
            
            // Clear previous results
            autocompleteContainer.innerHTML = '';
            
            if (searchTerm.length < 1) {
                return;
            }
            
            // Filter players based on search term and exclude already selected players
            const matchingPlayers = availablePlayers.filter(player => {
                // Skip if player is already in the tournament (except for the current input)
                if (tournamentParticipants.has(player) && this.value !== player) {
                    return false;
                }
                
                return player.toLowerCase().includes(searchTerm);
            });
            
            // Add Ghost Player option if it matches and not already used
            if ('Ghost Player'.toLowerCase().includes(searchTerm) && 
                (this.value === 'Ghost Player' || !tournamentParticipants.has('Ghost Player'))) {
                matchingPlayers.push('Ghost Player');
            }
            
            // Display matching players
            matchingPlayers.forEach(player => {
                const resultItem = document.createElement('div');
                
                // Highlight the matching part
                const matchIndex = player.toLowerCase().indexOf(searchTerm);
                resultItem.innerHTML = player.substring(0, matchIndex) +
                    '<strong>' + player.substring(matchIndex, matchIndex + searchTerm.length) + '</strong>' +
                    player.substring(matchIndex + searchTerm.length);
                
                resultItem.addEventListener('click', function() {
                    // Remove old value from participants if it exists
                    if (inputElement.dataset.previousValue && 
                        inputElement.dataset.previousValue !== "Ghost Player") {
                        tournamentParticipants.delete(inputElement.dataset.previousValue);
                    }
                    
                    // Add new value to participants if it's not Ghost Player
                    if (player !== "Ghost Player") {
                        tournamentParticipants.add(player);
                    }
                    
                    // Store current value for future reference
                    inputElement.dataset.previousValue = player;
                    
                    // Set input value
                    inputElement.value = player;
                    autocompleteContainer.innerHTML = '';
                    
                    // Trigger change event
                    const event = new Event('change', { bubbles: true });
                    inputElement.dispatchEvent(event);
                });
                
                autocompleteContainer.appendChild(resultItem);
            });
        });
        
        // Show search results when focusing on the input
        inputElement.addEventListener('focus', function() {
            const searchTerm = this.value.trim().toLowerCase();
            if (searchTerm.length >= 1) {
                // Trigger the input event to show results
                this.dispatchEvent(new Event('input'));
            }
        });
        
        // Hide search results when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target !== inputElement && !autocompleteContainer.contains(e.target)) {
                autocompleteContainer.innerHTML = '';
            }
        });
    }
    
    /**
     * Setup autocomplete for ace pot recipient input
     * Only shows players that are currently selected for the tournament
     * @param {HTMLElement} inputElement - The input element
     * @param {HTMLElement} autocompleteContainer - The autocomplete container
     */
    function setupAcePotRecipientAutocomplete(inputElement, autocompleteContainer) {
        // Remove existing event listeners (to prevent duplicates)
        const newInput = inputElement.cloneNode(true);
        inputElement.parentNode.replaceChild(newInput, inputElement);
        inputElement = newInput;
        
        // Clear the autocomplete container
        autocompleteContainer.innerHTML = '';
        
        inputElement.addEventListener('input', function() {
            const searchTerm = this.value.trim().toLowerCase();
            
            // Clear previous results
            autocompleteContainer.innerHTML = '';
            
            // Get current tournament participants (excluding Ghost Player)
            const currentParticipants = Array.from(tournamentParticipants).filter(player => player !== "Ghost Player");
            
            // Log for debugging
            console.log("Current tournament participants for ace pot:", currentParticipants);
            
            if (currentParticipants.length === 0) {
                // If no participants, show a message
                const noResults = document.createElement('div');
                noResults.textContent = "No players in tournament yet";
                noResults.style.padding = "10px";
                noResults.style.color = "#666";
                noResults.style.fontStyle = "italic";
                autocompleteContainer.appendChild(noResults);
                return;
            }
            
            // Filter participants based on search term
            const matchingPlayers = currentParticipants.filter(player => {
                return player.toLowerCase().includes(searchTerm.toLowerCase());
            });
            
            if (matchingPlayers.length === 0 && searchTerm.length > 0) {
                // If no matches, show a message
                const noResults = document.createElement('div');
                noResults.textContent = "No matching players";
                noResults.style.padding = "10px";
                noResults.style.color = "#666";
                noResults.style.fontStyle = "italic";
                autocompleteContainer.appendChild(noResults);
                return;
            }
            
            // Display matching players
            matchingPlayers.forEach(player => {
                const resultItem = document.createElement('div');
                
                if (searchTerm.length > 0) {
                    // Highlight the matching part
                    const matchIndex = player.toLowerCase().indexOf(searchTerm.toLowerCase());
                    resultItem.innerHTML = player.substring(0, matchIndex) +
                        '<strong>' + player.substring(matchIndex, matchIndex + searchTerm.length) + '</strong>' +
                        player.substring(matchIndex + searchTerm.length);
                } else {
                    resultItem.textContent = player;
                }
                
                resultItem.addEventListener('click', function() {
                    inputElement.value = player;
                    autocompleteContainer.innerHTML = '';
                });
                
                autocompleteContainer.appendChild(resultItem);
            });
        });
        
        // Show all participants when focusing on the input
        inputElement.addEventListener('focus', function() {
            // Trigger the input event to show all participants
            this.dispatchEvent(new Event('input'));
        });
        
        // Hide search results when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target !== inputElement && !autocompleteContainer.contains(e.target)) {
                autocompleteContainer.innerHTML = '';
            }
        });
    }
    
    /**
     * Update ace pot recipient inputs when tournament participants change
     */
    function updateAcePotRecipientInputs() {
        const recipientInputs = document.querySelectorAll('.ace-pot-recipient input');
        recipientInputs.forEach(input => {
            const autocompleteContainer = document.getElementById(`autocomplete_${input.id}`);
            if (autocompleteContainer) {
                // Re-initialize autocomplete with current participants
                setupAcePotRecipientAutocomplete(input, autocompleteContainer);
                
                // If the current value is not in the tournament participants, clear it
                if (input.value && input.value !== "Ghost Player" && 
                    !Array.from(tournamentParticipants).includes(input.value)) {
                    input.value = '';
                }
            }
        });
        
        // Log current tournament participants for debugging
        console.log("Tournament participants updated:", Array.from(tournamentParticipants));
    }
    
    /**
     * Add a new team row
     * @param {number} index - The team index
     * @param {Array} team - Optional team data for pre-populated teams
     */
    function addNewTeamRow(index, team = null) {
        const row = document.createElement('div');
        row.className = 'team-result';
        row.dataset.index = index;
        
        // Position number
        const positionSpan = document.createElement('span');
        positionSpan.className = 'position-number';
        positionSpan.textContent = (index + 1) + '.';
        
        // Team inputs container
        const teamInputs = document.createElement('div');
        teamInputs.className = 'team-inputs';
        
        // Player 1 input wrapper
        const player1Wrapper = document.createElement('div');
        player1Wrapper.className = 'player-input';
        
        const player1Input = document.createElement('input');
        player1Input.type = 'text';
        player1Input.name = `player1_${index}`;
        player1Input.id = `player1_${index}`;
        player1Input.placeholder = 'Player 1';
        player1Input.required = true;
        
        // Set value if pre-populated
        if (team && team.players && team.players[0]) {
            player1Input.value = team.players[0];
            
            // Add to tournament participants
            if (team.players[0] !== "Ghost Player") {
                tournamentParticipants.add(team.players[0]);
            }
            
            // Store current value for future reference
            player1Input.dataset.previousValue = team.players[0];
        }
        
        const autocomplete1 = document.createElement('div');
        autocomplete1.className = 'autocomplete-items';
        autocomplete1.id = `autocomplete_player1_${index}`;
        
        player1Wrapper.appendChild(player1Input);
        player1Wrapper.appendChild(autocomplete1);
        
        // Player 2 input wrapper
        const player2Wrapper = document.createElement('div');
        player2Wrapper.className = 'player-input';
        
        const player2Input = document.createElement('input');
        player2Input.type = 'text';
        player2Input.name = `player2_${index}`;
        player2Input.id = `player2_${index}`;
        player2Input.placeholder = 'Player 2';
        player2Input.required = true;
        
        // Set value if pre-populated
        if (team && team.players && team.players[1]) {
            player2Input.value = team.players[1];
            
            // Add to tournament participants
            if (team.players[1] !== "Ghost Player") {
                tournamentParticipants.add(team.players[1]);
            }
            
            // Store current value for future reference
            player2Input.dataset.previousValue = team.players[1];
        }
        
        const autocomplete2 = document.createElement('div');
        autocomplete2.className = 'autocomplete-items';
        autocomplete2.id = `autocomplete_player2_${index}`;
        
        player2Wrapper.appendChild(player2Input);
        player2Wrapper.appendChild(autocomplete2);
        
        // Score input
        const scoreInput = document.createElement('input');
        scoreInput.type = 'number';
        scoreInput.name = `score_${index}`;
        scoreInput.id = `score_${index}`;
        scoreInput.placeholder = 'Score';
        scoreInput.required = true;
        scoreInput.min = 1;
        
        // Set value if pre-populated
        if (team && team.score) {
            scoreInput.value = team.score;
        }
        
        // Remove button
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'remove-team';
        removeButton.innerHTML = '&times;';
        removeButton.title = 'Remove Team';
        
        removeButton.addEventListener('click', function() {
            // Remove players from tournament participants
            const player1 = player1Input.value;
            const player2 = player2Input.value;
            
            if (player1 && player1 !== "Ghost Player") {
                tournamentParticipants.delete(player1);
            }
            
            if (player2 && player2 !== "Ghost Player") {
                tournamentParticipants.delete(player2);
            }
            
            row.remove();
            updatePositionNumbers();
            
            // Update ace pot recipient inputs
            updateAcePotRecipientInputs();
        });
        
        // Assemble team inputs
        teamInputs.appendChild(player1Wrapper);
        teamInputs.appendChild(player2Wrapper);
        teamInputs.appendChild(scoreInput);
        teamInputs.appendChild(removeButton);
        
        // Assemble row
        row.appendChild(positionSpan);
        row.appendChild(teamInputs);
        
        // Add to container
        teamResultsContainer.appendChild(row);
        
        // Setup autocomplete
        setupPlayerAutocomplete(player1Input, autocomplete1);
        setupPlayerAutocomplete(player2Input, autocomplete2);
        
        // Add input event listeners to update tournament participants
        player1Input.addEventListener('change', function() {
            // Remove old value from participants if it exists
            if (this.dataset.previousValue && this.dataset.previousValue !== "Ghost Player") {
                tournamentParticipants.delete(this.dataset.previousValue);
            }
            
            // Add new value to participants if it's valid
            if (this.value && this.value !== "Ghost Player" && validatePlayerName(this.value)) {
                tournamentParticipants.add(this.value);
            }
            
            // Store current value for future reference
            this.dataset.previousValue = this.value;
            
            // Update ace pot recipient inputs
            updateAcePotRecipientInputs();
        });
        
        player2Input.addEventListener('change', function() {
            // Remove old value from participants if it exists
            if (this.dataset.previousValue && this.dataset.previousValue !== "Ghost Player") {
                tournamentParticipants.delete(this.dataset.previousValue);
            }
            
            // Add new value to participants if it's valid
            if (this.value && this.value !== "Ghost Player" && validatePlayerName(this.value)) {
                tournamentParticipants.add(this.value);
            }
            
            // Store current value for future reference
            this.dataset.previousValue = this.value;
            
            // Update ace pot recipient inputs
            updateAcePotRecipientInputs();
        });
    }
    
    /**
     * Update position numbers
     */
    function updatePositionNumbers() {
        const teamRows = document.querySelectorAll('.team-result');
        teamRows.forEach((row, index) => {
            const positionSpan = row.querySelector('.position-number');
            if (positionSpan) {
                positionSpan.textContent = (index + 1) + '.';
            }
            row.dataset.index = index;
        });
    }
});
