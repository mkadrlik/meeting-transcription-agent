using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading.Tasks;
using System.Threading;
using System.Text.Json;
using System.Collections.Generic;
using System.Collections.Concurrent;
using Whisper.net;
using Whisper.net.Ggml;

namespace MeetingTranscriptionAgent;

public class AudioStreamingServer
{
    private TcpListener? tcpListener;
    private bool isRunning = false;
    private WhisperProcessor? whisperProcessor;
    private readonly ConcurrentDictionary<string, ClientSession> clients = new();
    private readonly string modelFileName = "ggml-tiny.bin";
    private readonly int port;

    public AudioStreamingServer(int port = 8888)
    {
        this.port = port;
    }

    public async Task StartAsync()
    {
        try
        {
            // Initialize Whisper processor
            await InitializeWhisperAsync();

            // Start TCP listener
            tcpListener = new TcpListener(IPAddress.Any, port);
            tcpListener.Start();
            isRunning = true;
            
            Console.WriteLine($"Audio streaming server started on port {port}");
            Console.WriteLine("Waiting for client connections...");

            // Accept client connections
            while (isRunning)
            {
                try
                {
                    var tcpClient = await tcpListener.AcceptTcpClientAsync();
                    _ = Task.Run(async () => await HandleClientAsync(tcpClient));
                }
                catch (ObjectDisposedException)
                {
                    // Server is stopping
                    break;
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error starting server: {ex.Message}");
        }
    }

    private async Task InitializeWhisperAsync()
    {
        try
        {
            // Download model if it doesn't exist
            if (!File.Exists(modelFileName))
            {
                Console.WriteLine("Downloading Whisper model...");
                using var httpClient = new HttpClient();
                var downloader = new WhisperGgmlDownloader(httpClient);
                using var modelStream = await downloader.GetGgmlModelAsync(GgmlType.Tiny, QuantizationType.NoQuantization);
                using var fileStream = File.OpenWrite(modelFileName);
                await modelStream.CopyToAsync(fileStream);
                Console.WriteLine("Model downloaded successfully.");
            }

            // Initialize Whisper processor
            Console.WriteLine("Loading Whisper model...");
            using var factory = WhisperFactory.FromPath(modelFileName);
            whisperProcessor = factory.CreateBuilder()
                .WithLanguage("en")
                .Build();
            Console.WriteLine("Whisper model loaded successfully.");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error initializing Whisper: {ex.Message}");
            throw;
        }
    }

    private async Task HandleClientAsync(TcpClient tcpClient)
    {
        var clientId = Guid.NewGuid().ToString();
        var clientEndpoint = tcpClient.Client.RemoteEndPoint?.ToString() ?? "unknown";
        
        Console.WriteLine($"Client connected: {clientEndpoint} (ID: {clientId})");

        var session = new ClientSession
        {
            Id = clientId,
            TcpClient = tcpClient,
            NetworkStream = tcpClient.GetStream(),
            AudioBuffer = new List<byte>(),
            LastActivityTime = DateTime.UtcNow
        };

        clients.TryAdd(clientId, session);

        try
        {
            var buffer = new byte[4096];
            var messageBuffer = new List<byte>();
            
            while (tcpClient.Connected && isRunning)
            {
                int bytesRead = await session.NetworkStream.ReadAsync(buffer, 0, buffer.Length);
                
                if (bytesRead == 0)
                    break;

                session.LastActivityTime = DateTime.UtcNow;

                // Process incoming data
                await ProcessClientData(session, buffer, bytesRead);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error handling client {clientId}: {ex.Message}");
        }
        finally
        {
            Console.WriteLine($"Client disconnected: {clientEndpoint} (ID: {clientId})");
            clients.TryRemove(clientId, out _);
            tcpClient.Close();
        }
    }

    private async Task ProcessClientData(ClientSession session, byte[] buffer, int bytesRead)
    {
        // Look for JSON messages (terminated by newline)
        for (int i = 0; i < bytesRead; i++)
        {
            if (buffer[i] == '\n')
            {
                // Found message terminator
                var messageBytes = session.MessageBuffer.ToArray();
                session.MessageBuffer.Clear();

                if (messageBytes.Length > 0)
                {
                    try
                    {
                        string message = System.Text.Encoding.UTF8.GetString(messageBytes);
                        await ProcessClientMessage(session, message);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error processing message from {session.Id}: {ex.Message}");
                    }
                }
            }
            else
            {
                session.MessageBuffer.Add(buffer[i]);
            }
        }

        // If we're in audio data mode, add to audio buffer
        if (session.ExpectingAudioData > 0)
        {
            int audioDataStart = 0;
            
            // If we have leftover message data, skip it
            if (session.MessageBuffer.Count > 0)
            {
                audioDataStart = session.MessageBuffer.Count;
                session.MessageBuffer.Clear();
            }

            int audioDataSize = Math.Min(bytesRead - audioDataStart, session.ExpectingAudioData);
            
            for (int i = audioDataStart; i < audioDataStart + audioDataSize; i++)
            {
                session.AudioBuffer.Add(buffer[i]);
            }

            session.ExpectingAudioData -= audioDataSize;

            // If we have enough audio data, process it
            if (session.AudioBuffer.Count >= 16000 * 2 * 3) // ~3 seconds of audio
            {
                await ProcessAudioData(session);
            }
        }
    }

    private async Task ProcessClientMessage(ClientSession session, string message)
    {
        try
        {
            var json = JsonSerializer.Deserialize<JsonElement>(message);
            
            if (json.TryGetProperty("type", out var typeElement))
            {
                string messageType = typeElement.GetString() ?? "";

                switch (messageType)
                {
                    case "client_connect":
                        Console.WriteLine($"Client {session.Id} connected with audio format info");
                        await SendTranscriptionResult(session, "connection_confirmed", "Connected to transcription server");
                        break;

                    case "audio_data":
                        if (json.TryGetProperty("size", out var sizeElement))
                        {
                            session.ExpectingAudioData = sizeElement.GetInt32();
                        }
                        break;
                }
            }
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Invalid JSON from client {session.Id}: {ex.Message}");
        }
    }

    private async Task ProcessAudioData(ClientSession session)
    {
        if (whisperProcessor == null || session.AudioBuffer.Count < 1000)
            return;

        try
        {
            // Convert bytes to float array (assuming 16-bit PCM)
            var samples = new List<float>();
            
            for (int i = 0; i < session.AudioBuffer.Count - 1; i += 2)
            {
                short sample = (short)(session.AudioBuffer[i] | (session.AudioBuffer[i + 1] << 8));
                samples.Add(sample / 32768.0f);
            }

            // Clear the buffer
            session.AudioBuffer.Clear();

            if (samples.Count > 0)
            {
                // Transcribe using Whisper
                await foreach (var segment in whisperProcessor.ProcessAsync(samples.ToArray()))
                {
                    if (!string.IsNullOrWhiteSpace(segment.Text))
                    {
                        string transcriptionText = segment.Text.Trim();
                        Console.WriteLine($"[{session.Id}] {DateTime.Now:HH:mm:ss} {transcriptionText}");
                        
                        await SendTranscriptionResult(session, "transcription", transcriptionText);
                        
                        // Save to file
                        await SaveTranscription(session.Id, transcriptionText);
                    }
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error processing audio for {session.Id}: {ex.Message}");
        }
    }

    private async Task SendTranscriptionResult(ClientSession session, string type, string text)
    {
        try
        {
            var result = new
            {
                type = type,
                timestamp = DateTime.UtcNow,
                text = text
            };

            string json = JsonSerializer.Serialize(result);
            byte[] data = System.Text.Encoding.UTF8.GetBytes(json);
            
            await session.NetworkStream.WriteAsync(data, 0, data.Length);
            await session.NetworkStream.FlushAsync();
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error sending transcription to {session.Id}: {ex.Message}");
        }
    }

    private async Task SaveTranscription(string clientId, string text)
    {
        try
        {
            Directory.CreateDirectory("transcriptions");
            string timestamp = DateTime.Now.ToString("yyyyMMdd");
            string fileName = Path.Combine("transcriptions", $"meeting_transcription_{clientId}_{timestamp}.txt");
            
            string entry = $"[{DateTime.Now:HH:mm:ss}] {text}{Environment.NewLine}";
            await File.AppendAllTextAsync(fileName, entry);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error saving transcription: {ex.Message}");
        }
    }

    public void Stop()
    {
        isRunning = false;
        tcpListener?.Stop();
        
        // Close all client connections
        foreach (var session in clients.Values)
        {
            session.TcpClient.Close();
        }
        
        whisperProcessor?.Dispose();
        Console.WriteLine("Audio streaming server stopped.");
    }
}

public class ClientSession
{
    public string Id { get; set; } = "";
    public TcpClient TcpClient { get; set; } = null!;
    public NetworkStream NetworkStream { get; set; } = null!;
    public List<byte> AudioBuffer { get; set; } = new();
    public List<byte> MessageBuffer { get; set; } = new();
    public int ExpectingAudioData { get; set; } = 0;
    public DateTime LastActivityTime { get; set; }
}