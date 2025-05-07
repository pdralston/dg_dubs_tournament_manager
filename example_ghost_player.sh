#!/bin/bash
# Example script demonstrating the ghost player feature for odd numbers of players

echo "=== Ghost Player Feature Demonstration ==="
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
echo "Listing all players (7 players - odd number):"
python3 tournament_manager.py list

# Try to generate teams without ghost player (should fail)
echo ""
echo "Attempting to generate teams without ghost player:"
python3 tournament_manager.py teams John Sarah Mike Lisa Dave Amy Tom

# Generate teams with ghost player
echo ""
echo "Generating teams with ghost player:"
python3 tournament_manager.py teams John Sarah Mike Lisa Dave Amy Tom --allow-ghost

# Create a results file with ghost player
echo ""
echo "Creating tournament results file with ghost player..."
cat > ghost_results.txt << EOF
Mike,Lisa,52
John,Ghost Player,54
Dave,Amy,56
Sarah,Tom,58
EOF

# Record tournament results
echo ""
echo "Recording tournament results with ghost player:"
python3 tournament_manager.py record --file ghost_results.txt --course "Pine Valley" --date "2025-04-27"

# Show updated ratings
echo ""
echo "Updated player ratings (ghost player doesn't get rating updates):"
python3 tournament_manager.py list

# Show player details for someone who played with ghost
echo ""
echo "Player details for John (who played with ghost player):"
python3 tournament_manager.py details John

# Show tournament history
echo ""
echo "Tournament history (includes ghost player):"
python3 tournament_manager.py history

# Clean up temporary files
rm ghost_results.txt
