#!/bin/bash

# Test script for Meeting Transcription Agent

echo "Testing Meeting Transcription Agent..."

# Check if .NET is installed
if ! command -v dotnet &> /dev/null
then
    echo "ERROR: .NET is not installed. Please install .NET 8.0 SDK."
    exit 1
fi

echo "✓ .NET is installed"

# Check if required packages are installed
if [ ! -f "MeetingTranscriptionAgent.csproj" ]; then
    echo "ERROR: Project file not found."
    exit 1
fi

echo "✓ Project file found"

# Check if required NuGet packages are referenced
if ! grep -q "Whisper.net" MeetingTranscriptionAgent.csproj; then
    echo "ERROR: Whisper.net package not found in project."
    exit 1
fi

if ! grep -q "NAudio" MeetingTranscriptionAgent.csproj; then
    echo "ERROR: NAudio package not found in project."
    exit 1
fi

echo "✓ Required NuGet packages found"

# Check if transcriptions directory exists
if [ ! -d "transcriptions" ]; then
    echo "Creating transcriptions directory..."
    mkdir -p transcriptions
fi

echo "✓ Transcriptions directory ready"

echo "✓ Test completed. You can now run the application with:"
echo "  dotnet run"