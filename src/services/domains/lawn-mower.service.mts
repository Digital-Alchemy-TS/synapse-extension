import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type LawnMowerConfiguration<DATA extends object> = {
  /**
   * Current activity.
   */
  activity?: SettableConfiguration<"mowing" | "docked" | "paused" | "error", DATA>;
  supported_features?: number;
};

export type LawnMowerEvents = {
  start_mowing: {
    //
  };
  dock: {
    //
  };
  pause: {
    //
  };
};

export function VirtualLawnMower({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<LawnMowerConfiguration<object>, LawnMowerEvents>({
    bus_events: ["start_mowing", "dock", "pause"],
    context,
    // @ts-expect-error its fine
    domain: "lawn_mower",
    load_config_keys: ["activity", "supported_features"],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      LawnMowerConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      LawnMowerConfiguration<DATA>,
      LawnMowerEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
