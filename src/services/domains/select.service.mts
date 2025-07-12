import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  BuildCallbacks,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type SelectConfiguration<DATA extends object, OPTIONS extends string = string> = {
  /**
   * The current select option
   */
  current_option?: SettableConfiguration<OPTIONS, DATA>;
  /**
   * A list of available options as strings
   */
  options?: OPTIONS[];
  /**
   * default: true
   */
  managed?: boolean;
};

type SelectOptions = BasicAddParams & { options: string };

export type SelectEvents<OPTIONS extends string = string> = {
  select_option: { option: OPTIONS };
};

export function VirtualSelect({ context, synapse, logger }: TServiceParams) {
  const generate = synapse.generator.create<SelectConfiguration<object>, SelectEvents>({
    bus_events: ["select_option"],
    context,
    // @ts-expect-error its fine
    domain: "select",
    load_config_keys: ["current_option", "options"],
  });

  return function <
    PARAMS extends SelectOptions,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      SelectConfiguration<object>
    >,
  >({
    managed = true,
    ...options
  }: AddEntityOptions<
    SelectConfiguration<DATA, PARAMS["options"]>,
    SelectEvents<PARAMS["options"]>,
    PARAMS["attributes"],
    PARAMS["locals"],
    DATA
  >) {
    // @ts-expect-error it's fine
    const entity = generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);

    if (managed) {
      entity.onSelectOption(({ option }) => {
        logger.trace({ option }, "[managed] onSelectOption");
        entity.storage.set("current_option", option);
      });
    }
    type DynamicCallbacks = BuildCallbacks<SelectEvents<PARAMS["options"]>>;
    type TypedVirtualSelect = Omit<typeof entity, keyof DynamicCallbacks> &
      DynamicCallbacks &
      Omit<SelectConfiguration<DATA, PARAMS["options"]>, "managed">;

    return entity as TypedVirtualSelect;
  };
}
