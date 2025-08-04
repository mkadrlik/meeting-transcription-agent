# Use the official .NET 8.0 SDK image as the base
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

# Set the working directory
WORKDIR /app

# Copy the project files
COPY MeetingTranscriptionAgent.csproj ./
RUN dotnet restore

# Copy the rest of the project
COPY . ./

# Build the project
RUN dotnet publish -c Release -o out

# Create the runtime image
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime

# Install audio libraries and FFmpeg for Linux audio recording
RUN apt-get update && apt-get install -y \
    alsa-utils \
    libasound2 \
    libasound2-dev \
    pulseaudio \
    pulseaudio-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the published output from the build stage
COPY --from=build /app/out .

# Create the transcriptions directory
RUN mkdir -p transcriptions

# Set permissions for audio devices
RUN usermod -a -G audio root

# Set environment variables to help with audio library loading
ENV ALSA_PCM_CARD=0
ENV ALSA_PCM_DEVICE=0

# Expose any necessary ports (if needed for MCP server)
# EXPOSE 8080

# Set the entry point
ENTRYPOINT ["dotnet", "MeetingTranscriptionAgent.dll"]