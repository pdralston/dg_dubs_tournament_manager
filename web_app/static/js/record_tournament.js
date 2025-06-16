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
                        
                        // Add players to tournament participants set
                        if (player1Input.value !== "Ghost Player") {
                            tournamentParticipants.add(player1Input.value);
                        }
                        if (player2Input.value !== "Ghost Player") {
                            tournamentParticipants.add(player2Input.value);
                        }
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
        
        // Initialize autocomplete for this input
        setupPlayerAutocomplete(input, autocompleteContainer);
        
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
            }
            
            if (player2Input && autocomplete2) {
                setupPlayerAutocomplete(player2Input, autocomplete2);
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
            
            // Filter players based on search term
            const matchingPlayers = availablePlayers.filter(player => {
                return player.toLowerCase().includes(searchTerm);
            });
            
            // Add Ghost Player option if it matches
            if ('Ghost Player'.toLowerCase().includes(searchTerm)) {
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
                    inputElement.value = player;
                    autocompleteContainer.innerHTML = '';
                    inputElement.classList.remove('invalid');
                });
                
                autocompleteContainer.appendChild(resultItem);
            });
        });
        
        // Hide autocomplete when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target !== inputElement) {
                autocompleteContainer.innerHTML = '';
            }
        });
        
        // Show autocomplete on focus
        inputElement.addEventListener('focus', function() {
            const event = new Event('input');
            inputElement.dispatchEvent(event);
        });
    }
    
    /**
     * Adds a new team row to the form
     * @param {number} index - The team index
     * @param {Object} teamData - Optional team data for pre-populating
     */
    function addNewTeamRow(index, teamData = null) {
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
        player1Input.id = `player1_${index}`;
        player1Input.placeholder = 'Player 1';
        player1Input.required = true;
        
        // Create player 1 autocomplete container
        const autocomplete1 = document.createElement('div');
        autocomplete1.className = 'autocomplete-items';
        autocomplete1.id = `autocomplete_player1_${index}`;
        
        player1Wrapper.appendChild(player1Input);
        player1Wrapper.appendChild(autocomplete1);
        
        // Create player 2 input wrapper
        const player2Wrapper = document.createElement('div');
        player2Wrapper.className = 'player-input';
        
        // Create player 2 input
        const player2Input = document.createElement('input');
        player2Input.type = 'text';
        player2Input.name = `player2_${index}`;
        player2Input.id = `player2_${index}`;
        player2Input.placeholder = 'Player 2';
        player2Input.required = true;
        
        // Create player 2 autocomplete container
        const autocomplete2 = document.createElement('div');
        autocomplete2.className = 'autocomplete-items';
        autocomplete2.id = `autocomplete_player2_${index}`;
        
        player2Wrapper.appendChild(player2Input);
        player2Wrapper.appendChild(autocomplete2);
        
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
        setupPlayerAutocomplete(player1Input, autocomplete1);
        setupPlayerAutocomplete(player2Input, autocomplete2);
        
        // Set values if team data is provided
        if (teamData) {
            console.log('Setting team data:', teamData);
            
            // Handle different team data formats
            if (teamData.players && Array.isArray(teamData.players) && teamData.players.length >= 2) {
                // Format from team_results.html: { players: [player1, player2], ... }
                player1Input.value = teamData.players[0];
                player2Input.value = teamData.players[1];
            } else if (teamData.player1 && teamData.player2) {
                // Alternative format: { player1: "name1", player2: "name2" }
                player1Input.value = teamData.player1;
                player2Input.value = teamData.player2;
            } else {
                console.error('Invalid team data format:', teamData);
            }
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
