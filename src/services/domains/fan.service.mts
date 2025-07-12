import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type FanConfiguration<DATA extends object, PRESET_MODES extends string = string> = {
  /**
   * The current direction of the fan.
   */
  current_direction?: SettableConfiguration<string, DATA>;
  /**
   * True if the fan is on.
   */
  is_on?: SettableConfiguration<boolean, DATA>;
  /**
   * True if the fan is oscillating.
   */
  oscillating?: SettableConfiguration<boolean, DATA>;
  /**
   * The current speed percentage. Must be a value between 0 (off) and 100.
   */
  percentage?: SettableConfiguration<number, DATA>;
  /**
   * The current preset_mode. One of the values in preset_modes or None if no preset is active.
   */
  preset_mode?: SettableConfiguration<PRESET_MODES, DATA>;
  /**
   * The list of supported preset_modes. This is an arbitrary list of str and should not contain any speeds.
   */
  preset_modes?: PRESET_MODES[];
  /**
   * The number of speeds the fan supports.
   */
  speed_count?: number;
};

export type FanEvents = {
  set_direction: { direction: string };
  set_preset_mode: { preset_mode: string };
  set_percentage: { percentage: number };
  turn_on: {
    speed?: string;
    percentage?: number;
    preset_mode?: string;
  };
  turn_off: {
    //
  };
  toggle: {
    //
  };
  oscillate: { oscillating: boolean };
};

export function VirtualFan({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<FanConfiguration<object>, FanEvents>({
    bus_events: [
      "set_direction",
      "set_preset_mode",
      "set_percentage",
      "turn_on",
      "turn_off",
      "toggle",
      "oscillate",
    ],
    context,
    // @ts-expect-error its fine
    domain: "fan",
    load_config_keys: [
      "current_direction",
      "is_on",
      "oscillating",
      "percentage",
      "preset_mode",
      "preset_modes",
      "speed_count",
    ],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      FanConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      FanConfiguration<DATA>,
      FanEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
