/* eslint-disable sonarjs/pseudo-random */
import { SECOND, TServiceParams } from "@digital-alchemy/core";

type LocalData = {
  foo: number;
  bar: boolean;
};

type Attributes = {
  destination: string;
};

export function EntityGenerator({ scheduler, synapse, context, logger }: TServiceParams) {
  try {
    const subDevice = synapse.device.register("sub_device", {
      name: "example device",
      sw_version: "420.69",
    });
    const sensor = synapse.sensor<{ locals: LocalData; attributes: Attributes; state: number }>({
      attributes: {
        destination: "saturn",
      },
      context,
      device_class: "speed",
      device_id: subDevice,
      locals: {
        bar: false,
        foo: 5,
      },
      name: "Test the sensor",
      state: 20,
      suggested_object_id: "magic_the_sensor",
      unit_of_measurement: "ft/s",
    });

    sensor.onUpdate(() => {
      // sensor.u
    });

    const binary_sensor = synapse.binary_sensor({
      context,
      device_class: "window",
      name: "blinking",
      suggested_object_id: "blinking_the_binary_sensor",
    });
    // binary_sensor.is_on
    scheduler.setInterval(() => {
      const number = Math.floor(Math.random() * SECOND);
      sensor.storage.set("state", number);
      binary_sensor.storage.set("is_on", !binary_sensor.storage.get("is_on"));
    }, SECOND);
    const button = synapse.button({
      context,
      device_class: "identify",
      name: "example button",
      press() {
        logger.info("press()");
      },
      suggested_object_id: "button_the_example",
    });
    button.onPress(() => {
      logger.info("onPress()");
    });
    const scene = synapse.scene({
      activate() {
        logger.info("scene activated");
      },
      context,
      name: "Dynamic Scene",
      suggested_object_id: "setting_the_stage",
    });
    scene.onActivate(() => {
      logger.info("scene activated callback");
    });
    // const entity = hass.entity.byId("binary_sensor.hass_e2e_online");
    synapse.switch({
      context,
      icon: {
        current() {
          return binary_sensor.is_on ? "mdi:air-filter" : "mdi:account";
        },
        onUpdate: [binary_sensor],
      },
      is_on: {
        current() {
          return !binary_sensor.is_on;
        },
        onUpdate: [binary_sensor],
      },
      name: "Example switch",
    });
    // const acp = synapse.alarm_control_panel({
    // arm_night({ code }) {
    // logger.info({ code }, `arm_night called with code via static attachment`);
    // },
    // context,
    // name: "Example alarm panel",
    // });
    // acp.onArmNight(({ code }) =>
    // logger.info({ code }, `arm_night called with code via dynamic attachment`),
    // );
    synapse.lock({
      context,
      is_locked: false,
      name: "Example lock",
      suggested_object_id: "example_the_lock",
    });
    synapse.number({
      context,
      name: "Example number",
      native_max_value: 420,
      native_min_value: 69,
      native_value: 80,
      suggested_object_id: "example_the_number",
    });
    synapse.text({
      context,
      name: "Example text",
      native_value: "banana",
      suggested_object_id: "example_the_text",
    });
    synapse.select({
      context,
      current_option: "a",
      name: "Example select",
      options: ["a", "b", "c"],
      suggested_object_id: "example_the_select",
    });
    synapse.datetime({
      context,
      name: "Example datetime",
      suggested_object_id: "example_the_datetime",
    });
    synapse.date({
      context,
      name: "Example date",
      native_value: "2006-06-06",
      suggested_object_id: "example_the_date",
    });
    synapse.time({
      context,
      name: "Example time",
      native_value: "14:32:51",
      suggested_object_id: "example_the_time",
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error);
  }
}
