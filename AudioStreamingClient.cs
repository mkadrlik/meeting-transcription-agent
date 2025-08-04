using System;
using System.IO;
using System.Net.Sockets;
using System.Net;
using System.Threading.Tasks;
using System.Diagnostics;
using System.Threading;
using System.Text.Json;

namespace MeetingTranscriptionAgent;

public class AudioStreamingClient
{
    private TcpClient? tcpClient;
    private NetworkStream? networkStream;
    private Process? ffmpegProcess;
    private bool isStreaming = false;
    private string serverHost;
    private int serverPort;
    private CancellationTokenSource? cancellationTokenSource;

    public AudioStreamingClient(string host = "localhost", int port = 8888)
    {
        serverHost = host;
        serverPort = port;
    }

    public async Task StartStreamingAsync()
    {
        try
        {
            // Connect to transcription server
            Console.WriteLine($"Connecting to transcription server at {serverHost}:{serverPort}...");
            tcpClient = new TcpClient();
            await tcpClient.ConnectAsync(serverHost, serverPort);
            networkStream = tcpClient.GetStream();
            Console.WriteLine("Connected to transcription server.");

            // Send client info
            var clientInfo = new
            {
                type = "client_connect",
                timestamp = DateTime.UtcNow,
                audio_format = "pcm_s16le",
                sample_rate = 16000,
                channels = 1
            };
            
            await SendMessageAsync(JsonSerializer.Serialize(clientInfo));

            // Start audio capture and streaming
            cancellationTokenSource = new CancellationTokenSource();
            isStreaming = true;
            
            await StartAudioCapture();
            
            // Listen for transcription results
            _ = Task.Run(async () => await ListenForTranscriptions());
            
            Console.WriteLine("Audio streaming started. Press 'q' to stop...");
            
            // Wait for user input to stop
            await WaitForStopCommand();
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error starting audio streaming: {ex.Message}");
        }
        finally
        {
            await StopStreamingAsync();
        }
    }

    private async Task StartAudioCapture()
    {
        // Try different audio inputs (same as the main application)
        string[] audioInputOptions = {
            "-f alsa -i hw:2,0",           // Blue Microphones USB Audio
            "-f alsa -i hw:3,0",           // Depstech webcam MIC
            "-f alsa -i hw:1,0",           // HDA Analog
            "-f alsa -i hw:1,6",           // DMIC
            "-f alsa -i default",          // ALSA default
            "-f pulse -i default",         // PulseAudio default
        };

        foreach (string audioInput in audioInputOptions)
        {
            try
            {
                Console.WriteLine($"Trying audio input: {audioInput}");
                
                ffmpegProcess = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "ffmpeg",
                        Arguments = $"{audioInput} -acodec pcm_s16le -ar 16000 -ac 1 -f wav pipe:1",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true
                    }
                };

                ffmpegProcess.Start();
                
                // Wait a moment to see if the process starts successfully
                await Task.Delay(1000);
                
                if (!ffmpegProcess.HasExited)
                {
                    Console.WriteLine($"Successfully started audio capture with: {audioInput}");
                    
                    // Start streaming audio data
                    _ = Task.Run(async () => await StreamAudioData());
                    break;
                }
                else
                {
                    Console.WriteLine($"Failed to start with {audioInput}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error with {audioInput}: {ex.Message}");
            }
        }
    }

    private async Task StreamAudioData()
    {
        if (ffmpegProcess?.StandardOutput == null || networkStream == null)
            return;

        var buffer = new byte[4096];
        
        try
        {
            while (isStreaming && !cancellationTokenSource!.Token.IsCancellationRequested)
            {
                int bytesRead = await ffmpegProcess.StandardOutput.BaseStream.ReadAsync(
                    buffer, 0, buffer.Length, cancellationTokenSource.Token);
                
                if (bytesRead > 0)
                {
                    // Send audio data header
                    var audioHeader = new
                    {
                        type = "audio_data",
                        timestamp = DateTime.UtcNow,
                        size = bytesRead
                    };
                    
                    await SendMessageAsync(JsonSerializer.Serialize(audioHeader));
                    
                    // Send audio data
                    await networkStream.WriteAsync(buffer, 0, bytesRead, cancellationTokenSource.Token);
                    await networkStream.FlushAsync(cancellationTokenSource.Token);
                }
            }
        }
        catch (OperationCanceledException)
        {
            // Expected when stopping
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error streaming audio data: {ex.Message}");
        }
    }

    private async Task ListenForTranscriptions()
    {
        if (networkStream == null) return;

        var buffer = new byte[4096];
        
        try
        {
            while (isStreaming && !cancellationTokenSource!.Token.IsCancellationRequested)
            {
                int bytesRead = await networkStream.ReadAsync(buffer, 0, buffer.Length, cancellationTokenSource.Token);
                
                if (bytesRead > 0)
                {
                    string response = System.Text.Encoding.UTF8.GetString(buffer, 0, bytesRead);
                    
                    try
                    {
                        var transcriptionResult = JsonSerializer.Deserialize<TranscriptionResult>(response);
                        if (transcriptionResult?.type == "transcription" && !string.IsNullOrWhiteSpace(transcriptionResult.text))
                        {
                            Console.WriteLine($"[{transcriptionResult.timestamp:HH:mm:ss}] {transcriptionResult.text}");
                        }
                    }
                    catch (JsonException)
                    {
                        // Ignore malformed JSON
                    }
                }
            }
        }
        catch (OperationCanceledException)
        {
            // Expected when stopping
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error listening for transcriptions: {ex.Message}");
        }
    }

    private async Task SendMessageAsync(string message)
    {
        if (networkStream == null) return;
        
        var messageBytes = System.Text.Encoding.UTF8.GetBytes(message + "\n");
        await networkStream.WriteAsync(messageBytes, 0, messageBytes.Length);
        await networkStream.FlushAsync();
    }

    private async Task WaitForStopCommand()
    {
        await Task.Run(() =>
        {
            while (isStreaming)
            {
                var key = Console.ReadKey(true);
                if (key.KeyChar == 'q' || key.KeyChar == 'Q')
                {
                    Console.WriteLine("\nStopping audio streaming...");
                    break;
                }
            }
        });
    }

    public async Task StopStreamingAsync()
    {
        isStreaming = false;
        cancellationTokenSource?.Cancel();

        if (ffmpegProcess != null && !ffmpegProcess.HasExited)
        {
            ffmpegProcess.Kill();
            await ffmpegProcess.WaitForExitAsync();
        }

        networkStream?.Close();
        tcpClient?.Close();
        
        Console.WriteLine("Audio streaming stopped.");
    }
}

public class TranscriptionResult
{
    public string? type { get; set; }
    public DateTime timestamp { get; set; }
    public string? text { get; set; }
}