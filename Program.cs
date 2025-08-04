using System;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using System.Diagnostics;
using System.Threading;
using Whisper.net;
using Whisper.net.Ggml;

class Program
{
    private static Process? ffmpegProcess;
    private static string? outputFilePath;
    private static WhisperProcessor? whisperProcessor;
    private static bool isRecording = false;
    private static string modelFileName = "ggml-tiny.bin";
    private static HttpClient? httpClient;
    private static string tempAudioFile = "temp_recording.wav";
    private static CancellationTokenSource? cancellationTokenSource;

    static async Task Main(string[] args)
    {
        Console.WriteLine("Meeting Transcription Agent Starting...");

        // Create HttpClient for downloading models
        httpClient = new HttpClient();

        // Create transcriptions directory if it doesn't exist
        Directory.CreateDirectory("transcriptions");

        // Set up output file path with timestamp
        string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        outputFilePath = Path.Combine("transcriptions", $"meeting_transcription_{timestamp}.txt");

        try
        {
            // Check if FFmpeg is available
            if (!IsFFmpegAvailable())
            {
                Console.WriteLine("Error: FFmpeg is not available. Please install FFmpeg:");
                Console.WriteLine("Ubuntu/Debian: sudo apt-get install ffmpeg");
                Console.WriteLine("CentOS/RHEL: sudo yum install ffmpeg");
                Console.WriteLine("Or add FFmpeg to your Docker image.");
                return;
            }

            // Download Whisper model if it doesn't exist
            if (!File.Exists(modelFileName))
            {
                Console.WriteLine("Downloading Whisper model (this may take a few minutes)...");
                await DownloadModelAsync();
                Console.WriteLine("Model downloaded successfully.");
            }

            // Initialize Whisper processor
            Console.WriteLine("Loading Whisper model...");
            using var factory = WhisperFactory.FromPath(modelFileName);
            whisperProcessor = factory.CreateBuilder()
                .WithLanguage("en")
                .Build();
            Console.WriteLine("Whisper model loaded successfully.");

            Console.WriteLine("Press Enter to start recording... (Press 'q' then Enter to stop)");
            Console.ReadLine();

            // Start recording
            cancellationTokenSource = new CancellationTokenSource();
            await StartRecording();
            isRecording = true;

            Console.WriteLine("Recording started. Speak into your microphone...");
            Console.WriteLine("Press 'q' then Enter to stop recording.");

            // Wait for user to press 'q' to stop (Docker-friendly input handling)
            Console.WriteLine("Type 'q' and press Enter to stop, or press Ctrl+C");
            string? input = null;
            bool stopRequested = false;
            
            // Handle Ctrl+C gracefully
            Console.CancelKeyPress += (sender, e) => {
                e.Cancel = true;
                stopRequested = true;
                Console.WriteLine("\nStopping recording...");
            };
            
            while (!stopRequested)
            {
                if (Console.KeyAvailable)
                {
                    var key = Console.ReadKey(true);
                    if (key.KeyChar == 'q' || key.KeyChar == 'Q')
                    {
                        stopRequested = true;
                        Console.WriteLine("\nStopping recording...");
                        break;
                    }
                }
                
                // Also check for line input
                try
                {
                    if (Console.In.Peek() != -1)
                    {
                        input = Console.ReadLine();
                        if (input?.ToLower() == "q")
                        {
                            stopRequested = true;
                            break;
                        }
                    }
                }
                catch (InvalidOperationException)
                {
                    // Handle case where console input is redirected
                }
                
                await Task.Delay(100); // Small delay to prevent busy waiting
            }

            // Stop recording
            isRecording = false;
            await StopRecording();
            
            Console.WriteLine($"Recording stopped. Transcription saved to: {outputFilePath}");
            Console.WriteLine("Press any key to exit...");
            Console.ReadKey();
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
            Console.WriteLine("Make sure you have a working microphone and sufficient disk space for the model.");
        }
        finally
        {
            whisperProcessor?.Dispose();
            httpClient?.Dispose();
            cancellationTokenSource?.Dispose();
            
            // Clean up temp file
            if (File.Exists(tempAudioFile))
            {
                try { File.Delete(tempAudioFile); } catch { }
            }
        }
    }

    private static bool IsFFmpegAvailable()
    {
        try
        {
            var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "ffmpeg",
                    Arguments = "-version",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                }
            };
            process.Start();
            process.WaitForExit();
            return process.ExitCode == 0;
        }
        catch
        {
            return false;
        }
    }

    private static async Task DownloadModelAsync()
    {
        if (httpClient == null)
            throw new InvalidOperationException("HttpClient is not initialized");

        var downloader = new WhisperGgmlDownloader(httpClient);
        using var modelStream = await downloader.GetGgmlModelAsync(GgmlType.Tiny, QuantizationType.NoQuantization);
        using var fileStream = File.OpenWrite(modelFileName);
        await modelStream.CopyToAsync(fileStream);
    }

    private static async Task StartRecording()
    {
        // List of audio input options to try in order (based on detected devices)
        string[] audioInputOptions = {
            "-f alsa -i hw:2,0",           // Blue Microphones USB Audio
            "-f alsa -i hw:3,0",           // Depstech webcam MIC
            "-f alsa -i hw:1,0",           // HDA Analog
            "-f alsa -i hw:1,6",           // DMIC
            "-f alsa -i default",          // ALSA default
            "-f pulse -i default",         // PulseAudio default
        };

        bool recordingStarted = false;
        
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
                        Arguments = $"{audioInput} -acodec pcm_s16le -ar 16000 -ac 1 -t 10 -y {tempAudioFile}",
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
                    Console.WriteLine($"Successfully started recording with: {audioInput}");
                    recordingStarted = true;
                    
                    // Kill the test process and start the real recording
                    ffmpegProcess.Kill();
                    await ffmpegProcess.WaitForExitAsync();
                    
                    // Start the actual continuous recording
                    ffmpegProcess = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = "ffmpeg",
                            Arguments = $"{audioInput} -acodec pcm_s16le -ar 16000 -ac 1 -y {tempAudioFile}",
                            UseShellExecute = false,
                            RedirectStandardOutput = true,
                            RedirectStandardError = true,
                            CreateNoWindow = true
                        }
                    };
                    
                    ffmpegProcess.Start();
                    
                    // Start a background task to process audio periodically
                    _ = Task.Run(async () => await ProcessAudioPeriodically());
                    break;
                }
                else
                {
                    string stderr = await ffmpegProcess.StandardError.ReadToEndAsync();
                    Console.WriteLine($"Failed to start with {audioInput}, exit code: {ffmpegProcess.ExitCode}");
                    Console.WriteLine($"Error details: {stderr.Substring(0, Math.Min(200, stderr.Length))}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error with {audioInput}: {ex.Message}");
                if (ffmpegProcess != null && !ffmpegProcess.HasExited)
                {
                    try { ffmpegProcess.Kill(); } catch { }
                }
                ffmpegProcess = null;
            }
        }
        
        if (!recordingStarted)
        {
            throw new InvalidOperationException("Could not start audio recording with any available input method. Make sure a microphone is connected and working.");
        }
    }

    private static async Task StopRecording()
    {
        try
        {
            cancellationTokenSource?.Cancel();
            
            if (ffmpegProcess != null && !ffmpegProcess.HasExited)
            {
                ffmpegProcess.Kill();
                await ffmpegProcess.WaitForExitAsync();
            }
            
            // Process any remaining audio
            if (File.Exists(tempAudioFile))
            {
                await ProcessFinalAudio();
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error stopping recording: {ex.Message}");
        }
    }

    private static async Task ProcessAudioPeriodically()
    {
        while (isRecording && !cancellationTokenSource!.Token.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(5000, cancellationTokenSource.Token); // Wait 5 seconds
                
                if (isRecording && File.Exists(tempAudioFile))
                {
                    // Copy current recording to a temp file for processing
                    string processingFile = $"processing_{DateTime.Now.Ticks}.wav";
                    try
                    {
                        File.Copy(tempAudioFile, processingFile, true);
                        await ProcessAudioFile(processingFile);
                    }
                    finally
                    {
                        if (File.Exists(processingFile))
                        {
                            try { File.Delete(processingFile); } catch { }
                        }
                    }
                }
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error in periodic audio processing: {ex.Message}");
            }
        }
    }

    private static async Task ProcessFinalAudio()
    {
        try
        {
            await ProcessAudioFile(tempAudioFile);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error processing final audio: {ex.Message}");
        }
    }

    private static async Task ProcessAudioFile(string audioFilePath)
    {
        try
        {
            if (!File.Exists(audioFilePath) || whisperProcessor == null || outputFilePath == null)
                return;

            var fileInfo = new FileInfo(audioFilePath);
            if (fileInfo.Length < 1000) // Skip if file is too small
                return;

            // Read audio data and convert to float array
            var audioData = await File.ReadAllBytesAsync(audioFilePath);
            if (audioData.Length < 88) // Skip WAV header (44 bytes) + some audio data
                return;

            // Skip WAV header and convert to float array
            var samples = new List<float>();
            for (int i = 44; i < audioData.Length - 1; i += 2)
            {
                short sample = BitConverter.ToInt16(audioData, i);
                samples.Add(sample / 32768.0f);
            }

            if (samples.Count > 0)
            {
                // Transcribe using Whisper
                await foreach (var segment in whisperProcessor.ProcessAsync(samples.ToArray()))
                {
                    if (!string.IsNullOrWhiteSpace(segment.Text))
                    {
                        string recognizedText = $"[{DateTime.Now:HH:mm:ss}] {segment.Text.Trim()}";
                        Console.WriteLine($"Recognized: {recognizedText}");
                        await File.AppendAllTextAsync(outputFilePath, recognizedText + Environment.NewLine);
                    }
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error processing audio file: {ex.Message}");
        }
    }
}
