#!/bin/bash
# Example usage script for the Tournament-Style Disc Golf League Rating System

echo "=== Tournament-Style Disc Golf League Rating System Example ==="
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
python3 tournament_manager.py add "Kate" --rating 750

# List all players
echo ""
echo "Listing all players:"
python3 tournament_manager.py list

# Generate teams for a league night
echo ""
echo "Generating balanced teams for league night:"
python3 tournament_manager.py teams John Sarah Mike Lisa Dave Amy Tom Kate

# Create a teams file for prediction
echo ""
echo "Creating teams file for prediction..."
cat > teams.txt << EOF
John,Kate
Sarah,Tom
Mike,Lisa
Dave,Amy
EOF

# Predict tournament outcome
echo ""
echo "Predicting tournament outcome with par 54:"
python3 tournament_manager.py predict --file teams.txt --par 54

# Create a results file
echo ""
echo "Creating tournament results file..."
cat > results.txt << EOF
Mike,Lisa,52
John,Kate,54
Dave,Amy,56
Sarah,Tom,58
EOF

# Record tournament results
echo ""
echo "Recording tournament results:"
python3 tournament_manager.py record --file results.txt --course "Pine Valley" --date "2025-04-26"

# Show updated ratings
echo ""
echo "Updated player ratings:"
python3 tournament_manager.py list

# Show player details
echo ""
echo "Player details for Mike:"
python3 tournament_manager.py details Mike

# Show tournament history
echo ""
echo "Tournament history:"
python3 tournament_manager.py history

# Clean up temporary files
rm teams.txt results.txt
