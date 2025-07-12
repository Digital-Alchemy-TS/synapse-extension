import { TServiceParams } from "@digital-alchemy/core";
import { BinarySensorDeviceClass } from "@digital-alchemy/hass";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type BinarySensorConfiguration<DATA extends object> = {
  /**
   * Type of binary sensor.
   */
  device_class?: `${BinarySensorDeviceClass}`;
  /**
   * If the binary sensor is currently on or off.
   */
  is_on?: SettableConfiguration<boolean, DATA>;
};

export type BinarySensorEvents = {
  //
};

export function VirtualBinarySensor({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<BinarySensorConfiguration<object>, BinarySensorEvents>({
    context,
    default_config: { is_on: false },
    domain: "binary_sensor",
    load_config_keys: ["device_class", "is_on"],
  });

  return function <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      BinarySensorConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      BinarySensorConfiguration<DATA>,
      BinarySensorEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
