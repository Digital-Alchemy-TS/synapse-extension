import { TServiceParams } from "@digital-alchemy/core";
import { HVACAction, HVACMode } from "@digital-alchemy/hass";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type ClimateConfiguration<
  DATA extends object,
  PRESET_MODES extends string = string,
  SWING_MODES extends string = string,
  FAN_MODES extends string = string,
> = {
  /**
   * The current humidity.
   */
  current_humidity?: SettableConfiguration<number, DATA>;
  /**
   * The current temperature.
   */
  current_temperature?: SettableConfiguration<number, DATA>;
  /**
   * The current fan mode.
   */
  fan_mode?: SettableConfiguration<FAN_MODES, DATA>;
  /**
   * The list of available fan modes.
   */
  fan_modes?: FAN_MODES[];
  /**
   * The current HVAC action (heating, cooling)
   */
  hvac_action?: SettableConfiguration<HVACAction, DATA>;
  /**
   * The current operation (e.g. heat, cool, idle). Used to determine state.
   */
  hvac_mode: SettableConfiguration<HVACMode, DATA>;
  /**
   * List of available operation modes.
   */
  hvac_modes: HVACMode[];
  /**
   * The maximum humidity.
   */
  max_humidity?: number;
  /**
   * The maximum temperature in temperature_unit.
   */
  max_temp?: number;
  /**
   * The minimum humidity.
   */
  min_humidity?: number;
  /**
   * The minimum temperature in temperature_unit.
   */
  min_temp?: number;
  /**
   * The precision of the temperature in the system. Defaults to tenths for TEMP_CELSIUS, whole number otherwise.
   */
  precision?: number;
  /**
   * The current active preset.
   */
  preset_mode?: SettableConfiguration<PRESET_MODES, DATA>;
  /**
   * The available presets.
   */
  preset_modes?: PRESET_MODES[];
  /**
   * The swing setting.
   */
  swing_mode?: SettableConfiguration<SWING_MODES, DATA>;
  /**
   * Returns the list of available swing modes.
   */
  swing_modes?: SWING_MODES[];
  /**
   * The target humidity the device is trying to reach.
   */
  target_humidity?: SettableConfiguration<number, DATA>;
  /**
   * The temperature currently set to be reached.
   */
  target_temperature_high?: SettableConfiguration<number, DATA>;
  /**
   * The upper bound target temperature
   */
  target_temperature_low?: SettableConfiguration<number, DATA>;
  /**
   * The lower bound target temperature
   */
  target_temperature_step?: SettableConfiguration<number, DATA>;
  /**
   * The supported step size a target temperature can be increased or decreased
   */
  target_temperature?: SettableConfiguration<number, DATA>;
  /**
   * The unit of temperature measurement for the system (TEMP_CELSIUS or TEMP_FAHRENHEIT).
   */
  temperature_unit: string;
};

type ClimateEvents = {
  set_hvac_mode: {
    //
  };
  turn_on: {
    //
  };
  turn_off: {
    //
  };
  toggle: {
    //
  };
  set_preset_mode: {
    preset_mode: string;
  };
  set_fan_mode: {
    fan_mode: string;
  };
  set_humidity: {
    humidity: number;
  };
  set_swing_mode: {
    swing_mode: string;
  };
  set_temperature: {
    humidity: number;
  };
};

export function VirtualClimate({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<ClimateConfiguration<object>, ClimateEvents>({
    bus_events: [
      "set_hvac_mode",
      "turn_on",
      "turn_off",
      "toggle",
      "set_preset_mode",
      "set_fan_mode",
      "set_humidity",
      "set_swing_mode",
      "set_temperature",
    ],
    context,
    // @ts-expect-error it's fine
    domain: "climate",
    load_config_keys: [
      "current_humidity",
      "current_temperature",
      "fan_mode",
      "fan_modes",
      "hvac_action",
      "hvac_mode",
      "hvac_modes",
      "max_humidity",
      "max_temp",
      "min_humidity",
      "min_temp",
      "precision",
      "preset_mode",
      "preset_modes",
      "swing_mode",
      "swing_modes",
      "target_humidity",
      "target_temperature_high",
      "target_temperature_low",
      "target_temperature_step",
      "target_temperature",
      "temperature_unit",
    ],
  });

  return function <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      ClimateConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      ClimateConfiguration<DATA>,
      ClimateEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
