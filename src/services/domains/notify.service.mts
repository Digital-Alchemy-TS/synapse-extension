import { TServiceParams } from "@digital-alchemy/core";

import { AddEntityOptions, BasicAddParams, CallbackData } from "../../helpers/index.mts";

export type NotifyConfiguration = {
  //
};

export type NotifyEvents = {
  send_message: {
    message: string;
    title?: string;
  };
};

export function VirtualNotify({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<NotifyConfiguration, NotifyEvents>({
    bus_events: ["send_message"],
    context,
    // @ts-expect-error its fine
    domain: "notify",
    load_config_keys: [],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<PARAMS["locals"], PARAMS["attributes"], NotifyConfiguration>,
  >(
    options: AddEntityOptions<
      NotifyConfiguration,
      NotifyEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
