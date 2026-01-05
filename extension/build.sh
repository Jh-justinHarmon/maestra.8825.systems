#!/bin/bash
# Build Chrome extension

set -e

echo "Building Maestra Chrome Extension..."

# Build TypeScript
npx tsc --project tsconfig.json --outDir dist

# Copy manifest
cp manifest.json dist/

# Copy icons if they exist
if [ -d "images" ]; then
  cp -r images dist/
fi

echo "✓ Extension built to dist/"
echo "To load in Chrome:"
echo "  1. Open chrome://extensions"
echo "  2. Enable 'Developer mode'"
echo "  3. Click 'Load unpacked'"
echo "  4. Select the 'dist' folder"
