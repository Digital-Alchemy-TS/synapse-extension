import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type VacuumConfiguration<DATA extends object, FAN_SPEEDS extends string = string> = {
  /**
   * Current battery level.
   */
  battery_level?: SettableConfiguration<number, DATA>;
  /**
   * The current fan speed.
   */
  fan_speed?: SettableConfiguration<FAN_SPEEDS, DATA>;
  /**
   * List of available fan speeds.
   */
  fan_speed_list?: FAN_SPEEDS[];
  supported_features?: number;
};

export type VacuumEvents = {
  clean_spot: {
    //
  };
  locate: {
    //
  };
  pause: {
    //
  };
  return_to_base: {
    //
  };
  send_command: {
    //
  };
  set_fan_speed: {
    //
  };
  start: {
    //
  };
  stop: {
    //
  };
};

export function VirtualVacuum({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<VacuumConfiguration<object>, VacuumEvents>({
    bus_events: [
      "clean_spot",
      "locate",
      "pause",
      "return_to_base",
      "send_command",
      "set_fan_speed",
      "start",
      "stop",
    ],
    context,
    // @ts-expect-error its fine
    domain: "vacuum",
    load_config_keys: ["battery_level", "fan_speed", "fan_speed_list", "supported_features"],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      VacuumConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      VacuumConfiguration<DATA>,
      VacuumEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
