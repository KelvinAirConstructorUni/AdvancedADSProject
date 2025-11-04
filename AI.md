## Intelligent Route Planner

| System                                   | How It Works                                                                                       | You Can Simulate With                                                              |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Bluetooth Beacons (iBeacons)**         | Tiny BLE transmitters in each hallway broadcast IDs. Phone triangulates which one it’s closest to. | Pretend each building “emits” a signal → use simulated beacon zones on your map.   |
| **Wi-Fi Fingerprinting**                 | Measure strength of different Wi-Fi networks → compare to known map.                               | If you’re on campus Wi-Fi, request the BSSID via Python or JS and map it to rooms. |
| **Magnetic Mapping (IndoorAtlas style)** | Phones sense magnetic anomalies of steel structures.                                               | Hard to simulate, but you can randomize indoor drift to visualize “signal noise.”  |
| **Visual Markers (AR / QR)**             | Camera recognizes QR code or floor marker → knows exact room.                                      | Use mouse click as “scanned marker” for now.                                       |
| **Ultra-Wideband (UWB)**                 | High-freq radio pulses (like Apple AirTags).                                                       | Too hardware-specific, skip for now.                                               |
