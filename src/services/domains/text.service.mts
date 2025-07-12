import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type TextConfiguration<DATA extends object> = {
  /**
   * Defines how the text should be displayed in the UI. Can be text or password.
   */
  mode?: "text" | "password";
  /**
   * The maximum number of characters in the text value (inclusive).
   */
  native_max?: number;
  /**
   * The minimum number of characters in the text value (inclusive).
   */
  native_min?: number;
  /**
   * A regex pattern that the text value must match to be valid.
   */
  pattern?: SettableConfiguration<string, DATA>;
  /**
   * The value of the text.
   */
  native_value?: SettableConfiguration<string, DATA>;
  /**
   * default: true
   */
  managed?: boolean;
};

export type TextEvents = {
  set_value: { value: string };
};

export function VirtualText({ context, synapse, logger }: TServiceParams) {
  const generate = synapse.generator.create<TextConfiguration<object>, TextEvents>({
    bus_events: ["set_value"],
    context,
    // @ts-expect-error its fine
    domain: "text",
    load_config_keys: ["mode", "native_max", "native_min", "pattern", "native_value"],
  });

  return function <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      TextConfiguration<object>
    >,
  >({
    managed = true,
    ...options
  }: AddEntityOptions<
    TextConfiguration<DATA>,
    TextEvents,
    PARAMS["attributes"],
    PARAMS["locals"],
    DATA
  >) {
    // @ts-expect-error it's fine
    const entity = generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);

    if (managed) {
      entity.onSetValue(({ value }) => {
        logger.trace({ value }, "[managed] onSetValue");
        entity.storage.set("native_value", value);
      });
    }
    return entity;
  };
}
