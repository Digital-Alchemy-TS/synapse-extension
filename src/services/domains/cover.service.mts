import { TServiceParams } from "@digital-alchemy/core";
import { CoverDeviceClass } from "@digital-alchemy/hass";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type CoverConfiguration<DATA extends object> = {
  /**
   * The current position of cover where 0 means closed and 100 is fully open.
   */
  current_cover_position?: SettableConfiguration<number, DATA>;
  /**
   * The current tilt position of the cover where 0 means closed/no tilt and 100 means open/maximum tilt.
   */
  current_cover_tilt_position?: SettableConfiguration<number, DATA>;
  device_class?: `${CoverDeviceClass}`;
  /**
   * If the cover is closed or not. Used to determine state.
   */
  is_closed?: SettableConfiguration<boolean, DATA>;
  /**
   * If the cover is closing or not. Used to determine state.
   */
  is_closing?: SettableConfiguration<boolean, DATA>;
  /**
   * If the cover is opening or not. Used to determine state.
   */
  is_opening?: SettableConfiguration<boolean, DATA>;
};

export type CoverEvents = {
  stop_cover_tilt: {
    //
  };
  set_cover_tilt_position: {
    //
  };
  close_cover_tilt: {
    //
  };
  open_cover_tilt: {
    //
  };
  stop_cover: {
    //
  };
  set_cover_position: {
    //
  };
  close_cover: {
    //
  };
  open_cover: {
    //
  };
};

export function VirtualCover({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<CoverConfiguration<object>, CoverEvents>({
    bus_events: [
      "stop_cover_tilt",
      "set_cover_tilt_position",
      "close_cover_tilt",
      "open_cover_tilt",
      "stop_cover",
      "set_cover_position",
      "close_cover",
      "open_cover",
    ],
    context,
    // @ts-expect-error its fine
    domain: "cover",
    load_config_keys: [
      "current_cover_position",
      "current_cover_tilt_position",
      "device_class",
      "is_closed",
      "is_closing",
      "is_opening",
    ],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      CoverConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      CoverConfiguration<DATA>,
      CoverEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
