using System;
using System.Threading.Tasks;
using MeetingTranscriptionAgent;

class ProgramMain
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("=== Meeting Transcription Agent ===");
        Console.WriteLine("Select mode:");
        Console.WriteLine("1. Standalone (local microphone + transcription)");
        Console.WriteLine("2. Client (stream audio to remote server)");
        Console.WriteLine("3. Server (receive audio streams and transcribe)");
        Console.WriteLine();

        // Parse command line arguments or prompt user
        string mode = "";
        
        if (args.Length > 0)
        {
            mode = args[0].ToLower();
        }
        else
        {
            Console.Write("Enter mode (1, 2, or 3): ");
            string? input = Console.ReadLine();
            mode = input?.Trim() ?? "";
        }

        try
        {
            switch (mode)
            {
                case "1":
                case "standalone":
                    Console.WriteLine("Starting in standalone mode...");
                    await Program.Main(args);
                    break;

                case "2":
                case "client":
                    Console.WriteLine("Starting in client mode...");
                    await RunClientMode(args);
                    break;

                case "3":
                case "server":
                    Console.WriteLine("Starting in server mode...");
                    await RunServerMode(args);
                    break;

                default:
                    Console.WriteLine("Invalid mode. Please choose 1, 2, or 3.");
                    return;
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }
    }

    private static async Task RunClientMode(string[] args)
    {
        string serverHost = "localhost";
        int serverPort = 8888;

        // Parse additional arguments for server connection
        for (int i = 1; i < args.Length - 1; i++)
        {
            if (args[i] == "--host" || args[i] == "-h")
            {
                serverHost = args[i + 1];
            }
            else if (args[i] == "--port" || args[i] == "-p")
            {
                if (int.TryParse(args[i + 1], out int port))
                {
                    serverPort = port;
                }
            }
        }

        // If no host specified, prompt user
        if (serverHost == "localhost" && args.Length <= 1)
        {
            Console.Write("Enter server host (press Enter for localhost): ");
            string? hostInput = Console.ReadLine();
            if (!string.IsNullOrWhiteSpace(hostInput))
            {
                serverHost = hostInput;
            }

            Console.Write("Enter server port (press Enter for 8888): ");
            string? portInput = Console.ReadLine();
            if (!string.IsNullOrWhiteSpace(portInput) && int.TryParse(portInput, out int port))
            {
                serverPort = port;
            }
        }

        Console.WriteLine($"Connecting to transcription server at {serverHost}:{serverPort}");
        
        var client = new AudioStreamingClient(serverHost, serverPort);
        await client.StartStreamingAsync();
    }

    private static async Task RunServerMode(string[] args)
    {
        int serverPort = 8888;

        // Parse port argument
        for (int i = 1; i < args.Length - 1; i++)
        {
            if (args[i] == "--port" || args[i] == "-p")
            {
                if (int.TryParse(args[i + 1], out int port))
                {
                    serverPort = port;
                }
            }
        }

        // If no port specified, prompt user
        if (serverPort == 8888 && args.Length <= 1)
        {
            Console.Write("Enter server port (press Enter for 8888): ");
            string? portInput = Console.ReadLine();
            if (!string.IsNullOrWhiteSpace(portInput) && int.TryParse(portInput, out int port))
            {
                serverPort = port;
            }
        }

        Console.WriteLine($"Starting transcription server on port {serverPort}");
        Console.WriteLine("Press Ctrl+C to stop the server.");

        var server = new AudioStreamingServer(serverPort);
        
        // Handle graceful shutdown
        Console.CancelKeyPress += (sender, e) => {
            e.Cancel = true;
            Console.WriteLine("\nShutting down server...");
            server.Stop();
        };

        await server.StartAsync();
    }
}