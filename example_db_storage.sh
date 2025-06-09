#!/bin/bash
# Example script demonstrating the database storage feature

echo "=== Database Storage Feature Demonstration ==="
echo ""

# Add some players with different skill levels
echo "Adding players..."
python3 tournament_manager.py add "John" --rating 1100
python3 tournament_manager.py add "Sarah" --rating 1050
python3 tournament_manager.py add "Mike" --rating 1000
python3 tournament_manager.py add "Lisa" --rating 950
python3 tournament_manager.py add "Dave" --rating 900
python3 tournament_manager.py add "Amy" --rating 850
python3 tournament_manager.py add "Tom" --rating 800

# List all players
echo ""
echo "Listing all players (using database storage by default):"
python3 tournament_manager.py list

# Create a results file
echo ""
echo "Creating tournament results file..."
cat > db_results.txt << EOF
Mike,Lisa,52
John,Sarah,54
Dave,Amy,56
Tom,Ghost Player,58
EOF

# Record tournament results using database storage
echo ""
echo "Recording tournament results with database storage:"
python3 tournament_manager.py record --file db_results.txt --course "Pine Valley" --date "2025-04-28"

# Show updated ratings
echo ""
echo "Updated player ratings (database storage):"
python3 tournament_manager.py list

# Switch to JSON storage
echo ""
echo "Switching to JSON storage:"
python3 tournament_manager.py storage json

# List players from JSON
echo ""
echo "Listing all players (using JSON storage):"
python3 tournament_manager.py --use-json list

# Create another results file
echo ""
echo "Creating another tournament results file..."
cat > db_results2.txt << EOF
John,Sarah,51
Mike,Lisa,53
Dave,Amy,55
Tom,Ghost Player,57
EOF

# Record tournament results using JSON storage
echo ""
echo "Recording tournament results with JSON storage:"
python3 tournament_manager.py --use-json record --file db_results2.txt --course "Eagle Ridge" --date "2025-04-29"

# Show updated ratings from JSON
echo ""
echo "Updated player ratings (JSON storage):"
python3 tournament_manager.py --use-json list

# Show player details from JSON
echo ""
echo "Player details for John (from JSON):"
python3 tournament_manager.py --use-json details John

# Show tournament history from JSON
echo ""
echo "Tournament history (from JSON):"
python3 tournament_manager.py --use-json history

# Switch back to database storage
echo ""
echo "Switching back to database storage:"
python3 tournament_manager.py --use-json storage db

# Show player details from database
echo ""
echo "Player details for John (from database):"
python3 tournament_manager.py details John

# Clean up temporary files
rm db_results.txt db_results2.txt
