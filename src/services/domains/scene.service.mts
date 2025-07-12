import { TServiceParams } from "@digital-alchemy/core";
import { EmptyObject } from "type-fest";

import { AddEntityOptions, BasicAddParams, CallbackData } from "../../helpers/index.mts";

export type SceneConfiguration = EmptyObject;

export type SceneEvents = {
  activate: EmptyObject;
};

export function VirtualScene({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<SceneConfiguration, SceneEvents>({
    bus_events: ["activate"],
    context,
    domain: "scene",
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<PARAMS["locals"], PARAMS["attributes"], SceneConfiguration>,
  >(
    options: AddEntityOptions<
      SceneConfiguration,
      SceneEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => generate.addEntity(options);
}
