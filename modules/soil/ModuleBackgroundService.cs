using Microsoft.Azure.Devices.Client;
using Microsoft.Azure.Devices.Client.Transport.Mqtt;
using System.Text;
using System.Text.Json;

namespace soil;

internal class ModuleBackgroundService : BackgroundService
{
    private ModuleClient? _moduleClient;
    private CancellationToken _cancellationToken;
    private readonly ILogger<ModuleBackgroundService> _logger;
    private readonly Random _random = new();

    public ModuleBackgroundService(ILogger<ModuleBackgroundService> logger) => _logger = logger;

    protected override async Task ExecuteAsync(CancellationToken cancellationToken)
    {
        try
        {
            _logger.LogInformation("Starting ExecuteAsync in soil module...");

            _cancellationToken = cancellationToken;

            MqttTransportSettings mqttSetting = new(TransportType.Mqtt_Tcp_Only);
            ITransportSettings[] settings = { mqttSetting };

            _moduleClient = await ModuleClient.CreateFromEnvironmentAsync(settings);
            _moduleClient.SetConnectionStatusChangesHandler((status, reason) =>
                _logger.LogWarning("Connection changed: Status: {status} Reason: {reason}", status, reason));

            await _moduleClient.OpenAsync(cancellationToken);
            _logger.LogInformation("IoT Hub module client initialized.");

            double oximetry = 97.0;

            while (!cancellationToken.IsCancellationRequested)
            {
                oximetry += _random.Next(-5, 6) / 10.0;
                oximetry = Math.Clamp(oximetry, 0.0, 100.0);

                var oximetryData = new
                {
                    spo2 = Math.Round(oximetry, 1),
                    timestamp = DateTime.UtcNow
                };

                string messageString = JsonSerializer.Serialize(oximetryData);
                var messageBytes = Encoding.UTF8.GetBytes(messageString);
                using var message = new Message(messageBytes)
                {
                    ContentType = "application/json",
                    ContentEncoding = "utf-8"
                };

                await _moduleClient.SendEventAsync("output1", message, cancellationToken);
                _logger.LogInformation("Sent simulated SpO2: {OximetryData}", messageString);

                await Task.Delay(TimeSpan.FromSeconds(30), cancellationToken);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unhandled exception in ExecuteAsync");
            Console.WriteLine($"Unhandled exception: {ex.Message}");
        }
    }

}