#!/bin/bash

# Build script for Meeting Transcription Agent

echo "Building Meeting Transcription Agent..."

# Restore NuGet packages
echo "Restoring NuGet packages..."
dotnet restore

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to restore NuGet packages"
    exit 1
fi

echo "✓ NuGet packages restored"

# Build the project
echo "Building project..."
dotnet build --no-restore

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build project"
    exit 1
fi

echo "✓ Project built successfully"

echo "You can now run the application with:"
echo "  dotnet run"
echo ""
echo "Or run tests with:"
echo "  dotnet test"