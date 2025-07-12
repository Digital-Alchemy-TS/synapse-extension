import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";
import { DateConfiguration } from "./date.service.mts";

export type WaterHeaterConfiguration<DATA extends object, OPERATIONS extends string = string> = {
  /**
   * The minimum temperature that can be set.
   */
  min_temp?: number;
  /**
   * The maximum temperature that can be set.
   */
  max_temp?: number;
  /**
   * The current temperature.
   */
  current_temperature?: SettableConfiguration<number, DATA>;
  /**
   * The temperature we are trying to reach.
   */
  target_temperature?: SettableConfiguration<number, DATA>;
  /**
   * Upper bound of the temperature we are trying to reach.
   */
  target_temperature_high?: SettableConfiguration<number, DATA>;
  /**
   * Lower bound of the temperature we are trying to reach.
   */
  target_temperature_low?: SettableConfiguration<number, DATA>;
  /**
   * One of TEMP_CELSIUS, TEMP_FAHRENHEIT, or TEMP_KELVIN.
   */
  temperature_unit?: string;
  /**
   * The current operation mode.
   */
  current_operation?: SettableConfiguration<OPERATIONS, DATA>;
  /**
   * List of possible operation modes.
   */
  operation_list?: OPERATIONS[];
  /**
   * List of supported features.
   */
  supported_features?: number;
  is_away_mode_on?: SettableConfiguration<boolean, DATA>;
};

export type WaterHeaterEvents = {
  set_temperature: {
    //
  };
  set_operation_mode: {
    //
  };
  turn_away_mode_on: {
    //
  };
  turn_away_mode_off: {
    //
  };
  turn_on: {
    //
  };
  turn_off: {
    //
  };
};

export function VirtualWaterHeater({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<WaterHeaterConfiguration<object>, WaterHeaterEvents>({
    bus_events: [
      "set_temperature",
      "set_operation_mode",
      "turn_away_mode_on",
      "turn_away_mode_off",
      "turn_on",
      "turn_off",
    ],
    context,
    // @ts-expect-error its fine
    domain: "water_heater",
    load_config_keys: [
      "min_temp",
      "max_temp",
      "current_temperature",
      "target_temperature",
      "target_temperature_high",
      "target_temperature_low",
      "temperature_unit",
      "current_operation",
      "operation_list",
      "supported_features",
      "is_away_mode_on",
    ],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      DateConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      WaterHeaterConfiguration<DATA>,
      WaterHeaterEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
