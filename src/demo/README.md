# Synapse Demo App

This demo app creates example synapse entities for integration testing with real Home Assistant instances.

## Features

The demo app creates the following entities:

- **Demo Device**: A device that groups all demo entities
- **Temperature Sensor**: Updates every 30 seconds with simulated temperature variations
- **Motion Sensor**: Randomly toggles to simulate motion detection
- **Switch**: Can be controlled from Home Assistant
- **Button**: Logs when pressed and toggles the switch

## Usage

To run the demo app for integration testing:

```bash
# From the project root
npm run demo
# or
yarn demo
# or
pnpm demo
```

## Configuration

The demo app is configured with:
- Log level: `info`
- Device area: "Demo Room"
- Manufacturer: "Digital Alchemy"
- Model: "Synapse Demo"
- Unique ID: "synapse-demo-integration"

## Integration Testing

This demo app is designed for integration testing with real Home Assistant instances. It provides:

1. **Real-time entity updates**: Temperature sensor updates every 30 seconds
2. **Interactive controls**: Button and switch can be controlled from HA
3. **State persistence**: Entity states are persisted across restarts
4. **Error handling**: Proper error handling for async operations

## Entity IDs

The demo creates entities with the following object IDs:
- `demo_temperature_sensor`
- `demo_motion_sensor`
- `demo_switch`
- `demo_button`

These will appear in Home Assistant as:
- `sensor.demo_temperature_sensor`
- `binary_sensor.demo_motion_sensor`
- `switch.demo_switch`
- `button.demo_button`
