#!/bin/bash
sqlite3 tournament_data.db .dump > data_backup.sql
echo "Database backed up to data_backup.sql"
