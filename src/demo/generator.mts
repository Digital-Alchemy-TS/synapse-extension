/* eslint-disable @typescript-eslint/no-magic-numbers */
import { SECOND, TServiceParams } from "@digital-alchemy/core";

export function DemoEntityGenerator({ scheduler, synapse, context, logger }: TServiceParams) {
  try {
    logger.info("Starting demo entity generation...");

    // Create a device to group our entities
    const demoDevice = synapse.device.register("demo_device", {
      manufacturer: "Digital Alchemy",
      model: "Synapse Demo",
      name: "Synapse Demo Device",
      sw_version: "1.0.0",
    });

    // Create a temperature sensor that updates every 30 seconds
    const temperatureSensor = synapse.sensor<{ state: number }>({
      context,
      device_class: "temperature",
      device_id: demoDevice,
      name: "Demo Temperature Sensor",
      state: 22.5,
      suggested_object_id: "demo_temperature_sensor",
      unit_of_measurement: "°C",
    });

    // Create a binary sensor for demo purposes
    const motionSensor = synapse.binary_sensor({
      context,
      device_class: "motion",
      device_id: demoDevice,
      name: "Demo Motion Sensor",
      suggested_object_id: "demo_motion_sensor",
    });

    // Create a switch that can be controlled
    const demoSwitch = synapse.switch({
      context,
      device_id: demoDevice,
      is_on: false,
      name: "Demo Switch",
      suggested_object_id: "demo_switch",
    });

    // Create a button that logs when pressed
    const demoButton = synapse.button({
      context,
      device_class: "identify",
      device_id: demoDevice,
      name: "Demo Button",
      press() {
        logger.info("Demo button pressed!");
      },
      suggested_object_id: "demo_button",
    });

    // Set up periodic updates to simulate real device behavior
    scheduler.setInterval(() => {
      // Update temperature with some variation (safe for demo purposes)
      const currentTemp = temperatureSensor.state || 22.5;
      // eslint-disable-next-line sonarjs/pseudo-random
      const variation = (Math.random() - 0.5) * 2; // ±1°C variation
      const newTemp = Math.round((Number(currentTemp) + variation) * 10) / 10;
      temperatureSensor.state = newTemp;

      // Randomly toggle motion sensor (safe for demo purposes)
      // eslint-disable-next-line sonarjs/pseudo-random
      if (Math.random() > 0.8) {
        motionSensor.is_on = !motionSensor.is_on;
      }

      logger.debug("Updated demo entities", { temperature: newTemp });
    }, 30 * SECOND);

    // Set up button press callback
    demoButton.onPress(() => {
      logger.info("Demo button onPress callback triggered");
      // Toggle the switch when button is pressed
      const currentState = demoSwitch.is_on || false;
      demoSwitch.is_on = !currentState;
    });

    logger.info("Demo entity generation completed successfully");
  } catch (error) {
    logger.error("Error in demo entity generation", error);
    throw error;
  }
}
