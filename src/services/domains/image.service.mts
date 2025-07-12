import { TServiceParams } from "@digital-alchemy/core";
import { Dayjs } from "dayjs";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type ImageConfiguration<DATA extends object> = {
  /**
   * The content-type of the image, set automatically if the image entity provides a URL.
   */
  content_type?: SettableConfiguration<string, DATA>;
  /**
   * Timestamp of when the image was last updated. Used to determine state. Frontend will call image or async_image after this changes.
   */
  image_last_updated?: SettableConfiguration<Dayjs, DATA>;
  /**
   * Optional URL from where the image should be fetched.
   */
  image_url?: SettableConfiguration<string, DATA>;
};

export type ImageEvents = {
  //
};

export function VirtualImage({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<ImageConfiguration<object>, ImageEvents>({
    bus_events: [],
    context,
    // @ts-expect-error its fine
    domain: "image",
    load_config_keys: ["content_type", "image_last_updated", "image_url"],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      ImageConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      ImageConfiguration<DATA>,
      ImageEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
