import { TServiceParams } from "@digital-alchemy/core";
import { HumidifierDeviceClass } from "@digital-alchemy/hass";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type HumidifierConfiguration<DATA extends object> = {
  /**
   * Returns the current status of the device.
   */
  action?: SettableConfiguration<string, DATA>;
  /**
   * The available modes. Requires `SUPPORT_MODES`.
   */
  available_modes?: `${HumidifierModes}`[];
  /**
   * The current humidity measured by the device.
   */
  current_humidity?: SettableConfiguration<number, DATA>;
  /**
   * Type of hygrostat
   */
  device_class?: `${HumidifierDeviceClass}`;
  /**
   * Whether the device is on or off.
   */
  is_on?: SettableConfiguration<boolean, DATA>;
  /**
   * The maximum humidity.
   */
  max_humidity?: SettableConfiguration<number, DATA>;
  /**
   * The minimum humidity.
   */
  min_humidity?: SettableConfiguration<string, DATA>;
  /**
   * The current active mode. Requires `SUPPORT_MODES`.
   */
  mode?: SettableConfiguration<`${HumidifierModes}`, DATA>;
  /**
   * The target humidity the device is trying to reach.
   */
  target_humidity?: SettableConfiguration<number, DATA>;
};

export type HumidifierModes =
  | "normal"
  | "eco"
  | "away"
  | "boost"
  | "comfort"
  | "home"
  | "sleep"
  | "auto"
  | "baby";

export type HumidifierEvents = {
  set_humidity: {
    humidity: number;
  };
  turn_on: {
    //
  };
  turn_off: {
    //
  };
};

export function VirtualHumidifier({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<HumidifierConfiguration<object>, HumidifierEvents>({
    bus_events: ["set_humidity", "turn_on", "turn_off"],
    context,
    // @ts-expect-error its fine
    domain: "humidifier",
    load_config_keys: [
      "action",
      "available_modes",
      "current_humidity",
      "device_class",
      "is_on",
      "max_humidity",
      "min_humidity",
      "mode",
      "target_humidity",
    ],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      HumidifierConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      HumidifierConfiguration<DATA>,
      HumidifierEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
