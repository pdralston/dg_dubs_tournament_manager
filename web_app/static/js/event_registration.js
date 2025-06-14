/**
 * event_registration.js - Handles functionality for the event registration page
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const playerSearchInput = document.getElementById('player-search-input');
    const searchResults = document.getElementById('search-results');
    const selectedPlayersContainer = document.getElementById('selected-players-container');
    const eventRegistrationForm = document.getElementById('event-registration-form');
    
    // New player form elements
    const newPlayerName = document.getElementById('new-player-name');
    const newPlayerRating = document.getElementById('new-player-rating');
    const newPlayerClubMember = document.getElementById('new-player-club-member');
    const newPlayerAcePot = document.getElementById('new-player-ace-pot');
    const addNewPlayerBtn = document.getElementById('add-new-player-btn');
    
    // Ace pot elements
    const currentPotElement = document.getElementById('current-pot');
    const reservePotElement = document.getElementById('reserve-pot');
    const totalPotElement = document.getElementById('total-pot');
    const projectedPotElement = document.getElementById('projected-pot');
    
    // Track selected players
    const selectedPlayers = new Set();
    
    // Track ace pot contributions and get initial values
    let acePotContributions = 0;
    let currentPotValue = parseFloat(currentPotElement.textContent.replace('$', ''));
    let reservePotValue = parseFloat(reservePotElement.textContent.replace('$', ''));
    let totalPotValue = parseFloat(totalPotElement.textContent.replace('$', ''));
    
    // Get ace pot cap from the page
    const acePotCapText = document.querySelector('.ace-pot-cap span').textContent;
    const acePotCap = parseFloat(acePotCapText.replace('Ace Pot Cap: $', ''));
    
    // Initialize search functionality
    if (playerSearchInput) {
        playerSearchInput.addEventListener('input', function() {
            const searchTerm = this.value.trim().toLowerCase();
            
            // Clear previous results
            searchResults.innerHTML = '';
            
            if (searchTerm.length < 2) {
                return;
            }
            
            // Filter players based on search term
            const matchingPlayers = availablePlayers.filter(player => {
                // Skip already selected players
                if (selectedPlayers.has(player.name)) {
                    return false;
                }
                
                return player.name.toLowerCase().includes(searchTerm);
            });
            
            // Display matching players
            matchingPlayers.forEach(player => {
                const resultItem = document.createElement('div');
                
                // Highlight the matching part
                const matchIndex = player.name.toLowerCase().indexOf(searchTerm);
                resultItem.innerHTML = player.name.substring(0, matchIndex) +
                    '<strong>' + player.name.substring(matchIndex, matchIndex + searchTerm.length) + '</strong>' +
                    player.name.substring(matchIndex + searchTerm.length) +
                    ` <span class="player-rating">(${Math.round(player.rating)})</span>`;
                
                resultItem.addEventListener('click', function() {
                    addSelectedPlayer(player);
                    playerSearchInput.value = '';
                    searchResults.innerHTML = '';
                });
                
                searchResults.appendChild(resultItem);
            });
            
            // Show "Add New Player" option if no exact match
            const exactMatch = matchingPlayers.some(player => 
                player.name.toLowerCase() === searchTerm.toLowerCase()
            );
            
            if (!exactMatch && searchTerm.length > 0) {
                const addNewOption = document.createElement('div');
                addNewOption.className = 'add-new-option';
                addNewOption.innerHTML = `<strong>Add New Player:</strong> "${searchTerm}"`;
                
                addNewOption.addEventListener('click', function() {
                    newPlayerName.value = searchTerm;
                    newPlayerName.focus();
                    playerSearchInput.value = '';
                    searchResults.innerHTML = '';
                    
                    // Scroll to the add new player section
                    document.querySelector('.add-new-player').scrollIntoView({ behavior: 'smooth' });
                });
                
                searchResults.appendChild(addNewOption);
            }
        });
        
        // Show search results when focusing on the input
        playerSearchInput.addEventListener('focus', function() {
            const searchTerm = this.value.trim().toLowerCase();
            if (searchTerm.length >= 2) {
                // Trigger the input event to show results
                this.dispatchEvent(new Event('input'));
            }
        });
        
        // Hide search results when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target !== playerSearchInput && !searchResults.contains(e.target)) {
                searchResults.innerHTML = '';
            }
        });
    }
    
    // Add new player functionality
    if (addNewPlayerBtn) {
        addNewPlayerBtn.addEventListener('click', function() {
            const name = newPlayerName.value.trim();
            
            if (!name) {
                alert('Please enter a player name');
                return;
            }
            
            // Check if player already exists
            if (availablePlayers.some(player => player.name.toLowerCase() === name.toLowerCase())) {
                alert(`Player "${name}" already exists. Please select them from the search results.`);
                return;
            }
            
            // Create new player object
            const rating = newPlayerRating.value ? parseFloat(newPlayerRating.value) : 1000;
            const newPlayer = {
                name: name,
                rating: rating,
                is_club_member: newPlayerClubMember.checked,
                is_new_player: true
            };
            
            // Add to selected players
            addSelectedPlayer(newPlayer, newPlayerAcePot.checked);
            
            // Clear form
            newPlayerName.value = '';
            newPlayerRating.value = '';
            newPlayerClubMember.checked = false;
            newPlayerAcePot.checked = false;
        });
    }
    
    // Form submission
    if (eventRegistrationForm) {
        eventRegistrationForm.addEventListener('submit', function(e) {
            // Check if we have at least 2 players
            if (selectedPlayers.size < 2) {
                e.preventDefault();
                alert('Please select at least 2 players');
            }
        });
    }
    
    /**
     * Update the projected ace pot balance
     */
    function updateProjectedPot() {
        if (projectedPotElement && currentPotElement && reservePotElement) {
            // Calculate new projected total
            const projectedTotalValue = totalPotValue + acePotContributions;
            projectedPotElement.textContent = '$' + projectedTotalValue.toFixed(2);
            
            // Calculate new current pot (capped at acePotCap)
            const projectedCurrentValue = Math.min(projectedTotalValue, acePotCap);
            currentPotElement.textContent = '$' + projectedCurrentValue.toFixed(2);
            
            // Calculate new reserve pot
            const projectedReserveValue = Math.max(0, projectedTotalValue - acePotCap);
            reservePotElement.textContent = '$' + projectedReserveValue.toFixed(2);
            
            // Highlight the projected pot if it's different from the current total
            if (projectedTotalValue > totalPotValue) {
                projectedPotElement.classList.add('projected-increase');
                projectedPotElement.classList.remove('projected-decrease');
            } else if (projectedTotalValue < totalPotValue) {
                projectedPotElement.classList.add('projected-decrease');
                projectedPotElement.classList.remove('projected-increase');
            } else {
                projectedPotElement.classList.remove('projected-increase');
                projectedPotElement.classList.remove('projected-decrease');
            }
        }
    }
    
    /**
     * Handle ace pot checkbox change
     * @param {HTMLElement} checkbox - The ace pot checkbox element
     * @param {boolean} isChecked - Whether the checkbox is checked
     */
    function handleAcePotChange(checkbox, isChecked) {
        // Update ace pot contributions
        acePotContributions += isChecked ? 1 : -1;
        updateProjectedPot();
    }
    
    /**
     * Add a player to the selected players list
     * @param {Object} player - Player object
     * @param {boolean} acePotBuyIn - Whether the player is buying into the ace pot
     */
    function addSelectedPlayer(player, acePotBuyIn = false) {
        if (selectedPlayers.has(player.name)) {
            return;
        }
        
        // Add to selected players set
        selectedPlayers.add(player.name);
        
        // Create player element
        const playerElement = document.createElement('div');
        playerElement.className = 'selected-player';
        playerElement.dataset.playerName = player.name;
        
        // Player info
        const playerInfo = document.createElement('div');
        playerInfo.className = 'player-info';
        
        const playerName = document.createElement('div');
        playerName.className = 'player-name';
        playerName.textContent = player.name;
        
        const playerRating = document.createElement('div');
        playerRating.className = 'player-rating';
        playerRating.textContent = `Rating: ${Math.round(player.rating)}`;
        
        playerInfo.appendChild(playerName);
        playerInfo.appendChild(playerRating);
        
        // Player options
        const playerOptions = document.createElement('div');
        playerOptions.className = 'player-options';
        
        // Club member checkbox
        const clubMemberLabel = document.createElement('label');
        clubMemberLabel.className = 'checkbox-label';
        
        const clubMemberCheckbox = document.createElement('input');
        clubMemberCheckbox.type = 'checkbox';
        clubMemberCheckbox.name = `club_member_${player.name}`;
        clubMemberCheckbox.checked = player.is_club_member || false;
        
        clubMemberLabel.appendChild(clubMemberCheckbox);
        clubMemberLabel.appendChild(document.createTextNode('Club Member'));
        
        // Ace pot checkbox
        const acePotLabel = document.createElement('label');
        acePotLabel.className = 'checkbox-label';
        
        const acePotCheckbox = document.createElement('input');
        acePotCheckbox.type = 'checkbox';
        acePotCheckbox.name = `ace_pot_${player.name}`;
        acePotCheckbox.checked = acePotBuyIn;
        
        // Add event listener for ace pot checkbox
        acePotCheckbox.addEventListener('change', function() {
            handleAcePotChange(this, this.checked);
        });
        
        // If initially checked, update ace pot contributions
        if (acePotBuyIn) {
            handleAcePotChange(acePotCheckbox, true);
        }
        
        acePotLabel.appendChild(acePotCheckbox);
        acePotLabel.appendChild(document.createTextNode('Ace Pot'));
        
        // Remove button
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'remove-player';
        removeButton.innerHTML = '&times;';
        removeButton.title = 'Remove Player';
        
        removeButton.addEventListener('click', function() {
            // Check if ace pot checkbox was checked
            const acePotCheckbox = playerElement.querySelector(`input[name="ace_pot_${player.name}"]`);
            if (acePotCheckbox && acePotCheckbox.checked) {
                handleAcePotChange(acePotCheckbox, false);
            }
            
            playerElement.remove();
            selectedPlayers.delete(player.name);
        });
        
        // Add options to player element
        playerOptions.appendChild(clubMemberLabel);
        playerOptions.appendChild(acePotLabel);
        playerOptions.appendChild(removeButton);
        
        // Add hidden inputs for form submission
        const playerInput = document.createElement('input');
        playerInput.type = 'hidden';
        playerInput.name = 'players';
        playerInput.value = player.name;
        
        // Add is_new_player flag if applicable
        if (player.is_new_player) {
            const isNewPlayerInput = document.createElement('input');
            isNewPlayerInput.type = 'hidden';
            isNewPlayerInput.name = `is_new_player_${player.name}`;
            isNewPlayerInput.value = 'true';
            
            const ratingInput = document.createElement('input');
            ratingInput.type = 'hidden';
            ratingInput.name = `rating_${player.name}`;
            ratingInput.value = player.rating;
            
            playerElement.appendChild(isNewPlayerInput);
            playerElement.appendChild(ratingInput);
        }
        
        // Assemble player element
        playerElement.appendChild(playerInfo);
        playerElement.appendChild(playerOptions);
        playerElement.appendChild(playerInput);
        
        // Add to container
        selectedPlayersContainer.appendChild(playerElement);
    }
});
