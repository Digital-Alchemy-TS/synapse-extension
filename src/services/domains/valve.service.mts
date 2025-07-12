import { TServiceParams } from "@digital-alchemy/core";
import { ValveDeviceClass } from "@digital-alchemy/hass";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type ValveConfiguration<DATA extends object> = {
  /**
   * The current position of the valve where 0 means closed and 100 is fully open.
   * This attribute is required on valves with reports_position = True, where it's used to determine state.
   */
  current_valve_position?: SettableConfiguration<number, DATA>;
  /**
   * If the valve is closed or not. Used to determine state for valves that don't report position.
   */
  is_closed?: SettableConfiguration<boolean, DATA>;
  /**
   * If the valve is opening or not. Used to determine state.
   */
  is_opening?: SettableConfiguration<boolean, DATA>;
  /**
   * If the valve knows its position or not.
   */
  reports_position: SettableConfiguration<boolean, DATA>;
  device_class?: `${ValveDeviceClass}`;
  /**
   * If the valve is closing or not. Used to determine state.
   */
  is_closing?: SettableConfiguration<boolean, DATA>;
  supported_features?: number;
};

export type ValveEvents = {
  open_valve: {
    //
  };
  close_valve: {
    //
  };
  set_valve_position: {
    //
  };
  stop_valve: {
    //
  };
};

export function VirtualValve({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<ValveConfiguration<object>, ValveEvents>({
    bus_events: ["open_valve", "close_valve", "set_valve_position", "stop_valve"],
    context,
    // @ts-expect-error its fine
    domain: "valve",
    load_config_keys: [
      "current_valve_position",
      "is_closed",
      "is_opening",
      "reports_position",
      "device_class",
      "is_closing",
      "supported_features",
    ],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      ValveConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      ValveConfiguration<DATA>,
      ValveEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
