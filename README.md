# Meeting Transcription Agent

A C# application that listens to microphone input, transcribes speech in real-time using local speech recognition, and saves the transcription to timestamped files in a `transcriptions` folder.

## Features

- Real-time speech-to-text transcription using Whisper.NET (local processing)
- Continuous recording until user stops the application
- Automatic saving of transcriptions to timestamped files
- Simple console interface for starting/stopping recording
- No internet required for transcription (model runs locally)

## Prerequisites

- .NET 8.0 SDK
- Microphone access

## Setup

1. Clone this repository
2. No API keys or external services required - everything runs locally!

## Installation

```bash
# Run the build script
./build.sh
```

Or manually restore packages:
```bash
dotnet restore
```

On first run, the application will automatically download the Whisper model (approximately 75MB for the tiny model).

## Usage

```bash
# Test the application setup
./test-app.sh

# Run the application
dotnet run
```

1. Press Enter to start recording
2. Speak into your microphone
3. Press 'q' then Enter to stop recording
4. Transcription will be saved in the `transcriptions` folder

## Dependencies

- NAudio: For audio input handling
- Whisper.NET: For local speech recognition
- Whisper.NET.Runtime: For Whisper model runtime

## Model Information

The application uses the Whisper "tiny" model by default, which provides a good balance between accuracy and performance. The model will be automatically downloaded on first run.

Available models (trade-off between size, speed, and accuracy):
- tiny (75MB) - Fastest, least accurate
- base (142MB) - Good balance
- small (466MB) - More accurate, slower
- medium (1.5GB) - Very accurate, slow
- large (2.9GB) - Most accurate, slowest

To change the model, modify the `modelFileName` variable in Program.cs and update the `GgmlType` in the `DownloadModelAsync` method.

## Docker Support

This application includes Docker support for running in containerized environments.

Build the Docker image:
```bash
docker build -t meeting-transcription-agent .
```

Run the container:
```bash
docker run -it --device /dev/snd:/dev/snd meeting-transcription-agent
```

Note: The `--device /dev/snd:/dev/snd` flag is required to give the container access to audio devices.

## Docker Compose

You can also use docker-compose for easier deployment:

```bash
# Build and run with docker-compose
docker-compose up --build
```

## Project Structure

```
meeting-transcription-agent/
├── MeetingTranscriptionAgent.csproj  # Project file
├── Program.cs                        # Main application code
├── README.md                         # This file
├── Dockerfile                        # Docker configuration
├── docker-compose.yml                # Docker Compose configuration
├── .dockerignore                     # Docker ignore file
├── .gitignore                        # Git ignore file
├── .env.example                      # Example environment file
├── build.sh                          # Build script
├── test-app.sh                       # Test script
└── transcriptions/                   # Directory for saved transcriptions
    └── .gitkeep                      # Keeps the directory in Git