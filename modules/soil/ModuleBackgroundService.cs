﻿using Microsoft.Azure.Devices.Client;
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
        _cancellationToken = cancellationToken;

        // Configure MQTT transport settings
        MqttTransportSettings mqttSetting = new(TransportType.Mqtt_Tcp_Only);
        ITransportSettings[] settings = { mqttSetting };

        // Create the module client using environment variables (Edge runtime)
        _moduleClient = await ModuleClient.CreateFromEnvironmentAsync(settings);
        _moduleClient.SetConnectionStatusChangesHandler((status, reason) =>
            _logger.LogWarning("Connection changed: Status: {status} Reason: {reason}", status, reason));

        // Open the connection to IoT Edge runtime
        await _moduleClient.OpenAsync(cancellationToken);
        _logger.LogInformation("IoT Hub module client initialized.");

        double oximetry = 97.0; // Initial SpO2 value in percentage

        // Start the simulation loop
        while (!cancellationToken.IsCancellationRequested)
        {
            // Add a small random variation between -0.5% and +0.5%
            oximetry += _random.Next(-5, 6) / 10.0;

            // Clamp values between 0 and 100
            oximetry = Math.Clamp(oximetry, 0.0, 100.0);

            var oximetryData = new
            {
                spo2 = Math.Round(oximetry, 1),
                timestamp = DateTime.UtcNow
            };

            // Serialize the data to JSON
            string messageString = JsonSerializer.Serialize(oximetryData);
            var messageBytes = Encoding.UTF8.GetBytes(messageString);
            using var message = new Message(messageBytes)
            {
                ContentType = "application/json",
                ContentEncoding = "utf-8"
            };

            // Send the message to output1
            await _moduleClient.SendEventAsync("output1", message, cancellationToken);
            _logger.LogInformation("Sent simulated SpO2: {OximetryData}", messageString);

            // Wait 5 seconds before sending the next message
            await Task.Delay(TimeSpan.FromSeconds(30), cancellationToken);
        }
    }
}