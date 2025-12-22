#!/bin/bash
# Download the latest FAA NASR subscription and extract NAV.txt and FIX.txt

set -e

DATA_DIR="${1:-data}"
NASR_URL="https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/"

echo "Fetching latest NASR subscription ZIP download URL..."

# Get the latest ZIP download URL from the FAA NASR Subscription page (look for nfdc.faa.gov direct ZIP links)
ZIP_URL=$(curl -sL "$NASR_URL" | grep -oP 'https://nfdc\.faa\.gov/webContent/28DaySub/28DaySubscription_Effective_[0-9\-]+\.zip' | head -1)

if [ -z "$ZIP_URL" ]; then
    echo "Error: Could not find NASR subscription ZIP download link"
    exit 1
fi

echo "Downloading: $ZIP_URL"

mkdir -p "$DATA_DIR"
TEMP_ZIP=$(mktemp)

curl -L -o "$TEMP_ZIP" "$ZIP_URL"

echo "Extracting NAV.txt..."
unzip -p "$TEMP_ZIP" "NAV.txt" > "$DATA_DIR/NAV.txt" 2>/dev/null || \
unzip -p "$TEMP_ZIP" "*/NAV.txt" > "$DATA_DIR/NAV.txt"

echo "Extracting FIX.txt..."
unzip -p "$TEMP_ZIP" "FIX.txt" > "$DATA_DIR/FIX.txt" 2>/dev/null || \
unzip -p "$TEMP_ZIP" "*/FIX.txt" > "$DATA_DIR/FIX.txt"

rm "$TEMP_ZIP"

NAV_COUNT=$(grep -c "^NAV1" "$DATA_DIR/NAV.txt" || echo "0")
FIX_COUNT=$(grep -c "^FIX1" "$DATA_DIR/FIX.txt" || echo "0")
echo "Done. Extracted $NAV_COUNT NAVAIDs and $FIX_COUNT fixes to $DATA_DIR/"
