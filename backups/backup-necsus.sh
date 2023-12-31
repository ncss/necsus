#!/usr/bin/env bash

# Run this script to create a backup of the NeCSuS database (assuming it is called "necsus.db", in the usual place).
# Run it in a loop to create backups continuously:
#    while true; do sleep 15m; ./backup-necsus.sh; done

now=$(date +%Y-%m-%dT%H:%M:%S)
backup="$now.db"
sqlite3 ../necsus.db "VACUUM INTO '$backup'"
gzip $backup
echo "Backed up to $backup.gz"
