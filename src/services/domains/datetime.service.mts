import { TServiceParams } from "@digital-alchemy/core";
import dayjs, { ConfigType, Dayjs } from "dayjs";

import {
  AddEntityOptions,
  BasicAddParams,
  BuildCallbacks,
  CallbackData,
  SettableConfiguration,
  SynapseEntityException,
} from "../../helpers/index.mts";

type DateTimeSettable<DATA extends object> =
  | {
      date_type?: "iso";
      /**
       * iso date string
       */
      native_value?: SettableConfiguration<string, DATA>;
    }
  | {
      date_type: "dayjs";
      native_value?: SettableConfiguration<Dayjs, DATA>;
    }
  | {
      date_type: "date";
      native_value?: SettableConfiguration<Date, DATA>;
    };

export type DateTimeConfiguration<DATA extends object> = {
  /**
   * default: true
   */
  managed?: boolean;
} & DateTimeSettable<DATA>;

export type DateTimeEvents<VALUE extends SerializeTypes = string> = {
  set_value: { value: VALUE };
};

type TypeOptions = "dayjs" | "date" | "iso";

type DateTimeParams = BasicAddParams & {
  date_type?: TypeOptions;
};

type CallbackType<D extends TypeOptions = "iso"> = D extends "dayjs"
  ? Dayjs
  : D extends "date"
    ? Date
    : string;

type SerializeTypes = string | Date | Dayjs;

export function VirtualDateTime({ context, synapse, logger }: TServiceParams) {
  // #MARK: generator
  const generate = synapse.generator.create<
    DateTimeConfiguration<object>,
    DateTimeEvents,
    SerializeTypes
  >({
    bus_events: ["set_value"],
    context,
    // @ts-expect-error its fine
    domain: "datetime",
    load_config_keys: ["native_value"],
    serialize(property: keyof DateTimeConfiguration<object>, data: SerializeTypes) {
      if (property !== "native_value") {
        return data as string;
      }
      return dayjs(data).toISOString();
    },
    unserialize(
      property: keyof DateTimeConfiguration<object>,
      data: string,
      options: DateTimeConfiguration<object>,
    ): SerializeTypes {
      if (property !== "native_value") {
        return data as SerializeTypes;
      }
      const ref = dayjs(data);
      switch (options.date_type) {
        case "dayjs": {
          return ref;
        }
        case "date": {
          return ref.toDate();
        }
        default: {
          return ref.toISOString();
        }
      }
    },
    validate(
      current: DateTimeConfiguration<object>,
      key: keyof DateTimeConfiguration<object>,
      newValue: unknown,
    ) {
      if (key !== "native_value") {
        return true;
      }
      const incoming = dayjs(newValue as ConfigType);
      if (incoming.isValid()) {
        return true;
      }
      logger.error({ expected: current.date_type || "iso", newValue }, "unknown value type");
      throw new SynapseEntityException(
        context,
        "SET_INVALID_DATETIME",
        `Received invalid datetime format`,
      );
    },
  });

  // #MARK: builder
  return function <
    PARAMS extends DateTimeParams,
    DATA extends object = CallbackData<PARAMS["locals"], PARAMS["attributes"]>,
  >({
    managed = true,
    ...options
  }: AddEntityOptions<
    DateTimeConfiguration<DATA>,
    DateTimeEvents,
    PARAMS["attributes"],
    PARAMS["locals"],
    DATA
  >) {
    options.native_value ??= dayjs();
    // @ts-expect-error it's fine
    const entity = generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
    if (managed) {
      entity.onSetValue(({ value }) => {
        logger.trace({ value }, "[managed] onSetValue");
        entity.storage.set("native_value", value);
      });
    }
    type DynamicCallbacks = BuildCallbacks<DateTimeEvents<CallbackType<PARAMS["date_type"]>>>;
    type TypedVirtualDateTime = Omit<typeof entity, keyof DynamicCallbacks | "native_value"> &
      DynamicCallbacks & { native_value: CallbackType<PARAMS["date_type"]> };

    return entity as TypedVirtualDateTime;
  };
}
