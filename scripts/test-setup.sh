#!/bin/bash
# E2E Test Setup Script
# Starts mock backend and main app for testing

set -e

echo "Starting mock backend..."
cd mock-backend
npm install > /dev/null 2>&1 || true
npm run start &
BACKEND_PID=$!

echo "Waiting for backend to be ready..."
sleep 2

# Check if backend is running
if ! curl -s http://localhost:3001/health > /dev/null; then
  echo "❌ Backend failed to start"
  kill $BACKEND_PID 2>/dev/null || true
  exit 1
fi

echo "✅ Backend running on port 3001"
cd ..

echo "Starting main app..."
npm run dev &
APP_PID=$!

echo "Waiting for app to be ready..."
sleep 3

# Check if app is running
if ! curl -s http://localhost:5000 > /dev/null; then
  echo "❌ App failed to start"
  kill $APP_PID $BACKEND_PID 2>/dev/null || true
  exit 1
fi

echo "✅ App running on port 5000"

echo ""
echo "Running E2E tests..."
npx playwright test

# Cleanup
echo ""
echo "Cleaning up..."
kill $APP_PID $BACKEND_PID 2>/dev/null || true
