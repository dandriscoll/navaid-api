#!/bin/bash
# Update NAVAID data from FAA NASR subscription
# Run via cron: 0 3 * * 0 /opt/navaid-api/update-data.sh

set -e

DATA_DIR="${1:-/var/lib/navaid-api}"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Download new data to temp location
TEMP_DIR=$(mktemp -d)
"$SCRIPT_DIR/download-nasr.sh" "$TEMP_DIR"

# Compare with existing
if [ -f "$DATA_DIR/NAV.txt" ]; then
    OLD_HASH=$(md5sum "$DATA_DIR/NAV.txt" | cut -d' ' -f1)
    NEW_HASH=$(md5sum "$TEMP_DIR/NAV.txt" | cut -d' ' -f1)

    if [ "$OLD_HASH" = "$NEW_HASH" ]; then
        echo "Data unchanged, skipping update"
        rm -rf "$TEMP_DIR"
        exit 0
    fi
fi

# Update data file
mv "$TEMP_DIR/NAV.txt" "$DATA_DIR/NAV.txt"
rm -rf "$TEMP_DIR"

# Restart service if running
if systemctl is-active --quiet navaid-api; then
    echo "Restarting navaid-api service..."
    systemctl restart navaid-api
fi

echo "Update complete"
