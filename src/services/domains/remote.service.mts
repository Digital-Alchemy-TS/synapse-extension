import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type RemoteConfiguration<DATA extends object> = {
  /**
   * Return the current active activity
   */
  current_activity?: SettableConfiguration<string, DATA>;
  /**
   * Return the list of available activities
   */
  activity_list?: string[];
  supported_features?: number;
};

export type RemoteEvents = {
  turn_on: { activity?: string };
  turn_off: { activity?: string };
  toggle: { activity?: string };
  send_command: { command: string[] };
  learn_command: {
    //
  };
  delete_command: {
    //
  };
};

export function VirtualRemote({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<RemoteConfiguration<object>, RemoteEvents>({
    bus_events: [
      "turn_on",
      "turn_off",
      "toggle",
      "send_command",
      "learn_command",
      "delete_command",
    ],
    context,
    // @ts-expect-error its fine
    domain: "remote",
    load_config_keys: ["current_activity", "activity_list", "supported_features"],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      RemoteConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      RemoteConfiguration<DATA>,
      RemoteEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
