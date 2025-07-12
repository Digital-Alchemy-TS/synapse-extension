import { TServiceParams } from "@digital-alchemy/core";
import { SwitchDeviceClass } from "@digital-alchemy/hass";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type SwitchConfiguration<DATA extends object> = {
  device_class?: `${SwitchDeviceClass}`;
  /**
   * If the switch is currently on or off.
   */
  is_on?: SettableConfiguration<boolean, DATA>;
  /**
   * default: true
   */
  managed?: boolean;
};

export type SwitchEvents = {
  turn_on: {
    //
  };
  turn_off: {
    //
  };
  toggle: {
    //
  };
};

export function VirtualSwitch({ context, synapse, logger }: TServiceParams) {
  const generate = synapse.generator.create<SwitchConfiguration<object>, SwitchEvents>({
    bus_events: ["turn_on", "turn_off", "toggle"],
    context,
    domain: "switch",
    load_config_keys: ["device_class", "is_on"],
  });

  return function <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      SwitchConfiguration<object>
    >,
  >({
    managed = true,
    ...options
  }: AddEntityOptions<
    SwitchConfiguration<DATA>,
    SwitchEvents,
    PARAMS["attributes"],
    PARAMS["locals"],
    DATA
  >) {
    // @ts-expect-error it's fine
    const entity = generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
    if (managed) {
      entity.onToggle(() => {
        logger.trace("[managed] onToggle");
        entity.storage.set("is_on", !entity.storage.get("is_on"));
      });
      entity.onTurnOff(() => {
        logger.trace("[managed] onTurnOff");
        entity.storage.set("is_on", false);
      });
      entity.onTurnOn(() => {
        logger.trace("[managed] onTurnOn");
        entity.storage.set("is_on", true);
      });
    }
    return entity;
  };
}
