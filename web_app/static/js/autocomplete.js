/**
 * autocomplete.js - Provides autocomplete functionality for player input fields
 */
class PlayerAutocomplete {
    /**
     * Initialize autocomplete for player input fields
     * @param {HTMLElement} inputElement - The input element to attach autocomplete to
     * @param {Array} players - Array of valid player names
     * @param {Function} onValidationChange - Callback when validation state changes
     */
    constructor(inputElement, players, onValidationChange = null) {
        this.input = inputElement;
        this.players = players;
        this.onValidationChange = onValidationChange;
        this.isValid = false;
        
        // Create autocomplete container
        this.autocompleteContainer = document.createElement('div');
        this.autocompleteContainer.className = 'autocomplete-items';
        this.input.parentNode.appendChild(this.autocompleteContainer);
        
        // Create validation message element
        this.validationMessage = document.createElement('div');
        this.validationMessage.className = 'validation-message';
        this.input.parentNode.appendChild(this.validationMessage);
        
        // Add event listeners
        this.addEventListeners();
    }
    
    /**
     * Add event listeners to the input element
     */
    addEventListeners() {
        // Input event for filtering suggestions
        this.input.addEventListener('input', () => {
            this.filterSuggestions();
            this.validateInput();
        });
        
        // Focus event to show suggestions
        this.input.addEventListener('focus', () => {
            this.filterSuggestions();
        });
        
        // Blur event to hide suggestions and validate
        this.input.addEventListener('blur', () => {
            // Delay closing to allow clicking on suggestions
            setTimeout(() => {
                this.closeAllLists();
                this.validateInput(true);
            }, 200);
        });
        
        // Key navigation
        this.input.addEventListener('keydown', (e) => {
            let items = this.autocompleteContainer.getElementsByTagName('div');
            if (e.key === 'ArrowDown') {
                this.currentFocus++;
                this.addActive(items);
                e.preventDefault();
            } else if (e.key === 'ArrowUp') {
                this.currentFocus--;
                this.addActive(items);
                e.preventDefault();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (this.currentFocus > -1) {
                    if (items[this.currentFocus]) {
                        items[this.currentFocus].click();
                    }
                }
            }
        });
    }
    
    /**
     * Update the options for this autocomplete
     * @param {Array} newOptions - New array of valid options
     */
    updateOptions(newOptions) {
        this.players = newOptions;
        this.validateInput();
    }
    
    /**
     * Filter and display suggestions based on input value
     */
    filterSuggestions() {
        const inputValue = this.input.value.trim();
        this.closeAllLists();
        
        if (!inputValue) {
            return;
        }
        
        this.currentFocus = -1;
        
        // Filter players that match the input
        const matchingPlayers = this.players.filter(player => 
            player.toLowerCase().includes(inputValue.toLowerCase())
        );
        
        // Add Ghost Player option if it matches
        if ('Ghost Player'.toLowerCase().includes(inputValue.toLowerCase())) {
            matchingPlayers.push('Ghost Player');
        }
        
        // Display matching players
        matchingPlayers.forEach(player => {
            const item = document.createElement('div');
            
            // Highlight the matching part
            const matchIndex = player.toLowerCase().indexOf(inputValue.toLowerCase());
            item.innerHTML = player.substring(0, matchIndex) +
                '<strong>' + player.substring(matchIndex, matchIndex + inputValue.length) + '</strong>' +
                player.substring(matchIndex + inputValue.length);
            
            // Add click event to select this item
            item.addEventListener('click', () => {
                this.input.value = player;
                this.closeAllLists();
                this.validateInput();
                this.input.focus();
            });
            
            this.autocompleteContainer.appendChild(item);
        });
    }
    
    /**
     * Close all autocomplete lists
     */
    closeAllLists() {
        this.autocompleteContainer.innerHTML = '';
    }
    
    /**
     * Add active class to the current focus item
     * @param {HTMLCollection} items - The list items
     */
    addActive(items) {
        if (!items) return;
        
        // Remove active from all items
        for (let i = 0; i < items.length; i++) {
            items[i].classList.remove('autocomplete-active');
        }
        
        // Add active to current focus
        if (this.currentFocus >= items.length) this.currentFocus = 0;
        if (this.currentFocus < 0) this.currentFocus = items.length - 1;
        
        if (items[this.currentFocus]) {
            items[this.currentFocus].classList.add('autocomplete-active');
        }
    }
    
    /**
     * Validate the current input value
     * @param {boolean} showError - Whether to show error message
     * @returns {boolean} - Whether the input is valid
     */
    validateInput(showError = false) {
        const value = this.input.value.trim();
        
        // Empty is invalid
        if (!value) {
            this.isValid = false;
            if (showError) {
                this.showError('Player name is required');
            }
            return false;
        }
        
        // Check if value is in players list or is "Ghost Player"
        const isValid = this.players.includes(value) || value === 'Ghost Player';
        this.isValid = isValid;
        
        if (!isValid && showError) {
            this.showError('Invalid player name');
        } else {
            this.hideError();
        }
        
        // Call validation change callback if provided
        if (this.onValidationChange) {
            this.onValidationChange(this.isValid);
        }
        
        return isValid;
    }
    
    /**
     * Show error message
     * @param {string} message - The error message
     */
    showError(message) {
        this.validationMessage.textContent = message;
        this.validationMessage.style.display = 'block';
        this.input.classList.add('invalid');
    }
    
    /**
     * Hide error message
     */
    hideError() {
        this.validationMessage.style.display = 'none';
        this.input.classList.remove('invalid');
    }
}
