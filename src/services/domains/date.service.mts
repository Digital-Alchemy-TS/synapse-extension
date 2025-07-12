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
import { DateTimeConfiguration } from "./datetime.service.mts";

type Year = `${number}${number}${number}${number}`;
type MD = `${number}${number}`;
/**
 * YYYY-MM-DD
 */
export type SynapseDateFormat = `${Year}-${MD}-${MD}`;

export type DateConfiguration<DATA extends object> = {
  /**
   * default: true
   */
  managed?: boolean;
} & DateSettable<DATA>;

export type DateEvents<VALUE extends SerializeTypes = SynapseDateFormat> = {
  set_value: { value: VALUE };
};

type TypeOptions = "dayjs" | "date" | "iso";

type DateParams = BasicAddParams & {
  date_type?: TypeOptions;
};
type SerializeTypes = SynapseDateFormat | Date | Dayjs;

type DateSettable<DATA extends object> =
  | { date_type?: "iso"; native_value?: SettableConfiguration<SynapseDateFormat, DATA> }
  | { date_type: "dayjs"; native_value?: SettableConfiguration<Dayjs, DATA> }
  | { date_type: "date"; native_value?: SettableConfiguration<Date, DATA> };

const FORMAT = "YYYY-MM-DD";

type CallbackType<D extends TypeOptions = "iso"> = D extends "dayjs"
  ? Dayjs
  : D extends "date"
    ? Date
    : SynapseDateFormat;

export function VirtualDate({ context, synapse, logger }: TServiceParams) {
  // #MARK: generator
  const generate = synapse.generator.create<DateConfiguration<object>, DateEvents, SerializeTypes>({
    bus_events: ["set_value"],
    context,
    // @ts-expect-error its fine
    domain: "date",
    load_config_keys: ["native_value"],
    serialize(property: keyof DateConfiguration<object>, data: SerializeTypes) {
      if (property !== "native_value") {
        return data as string;
      }
      return dayjs(data).format(FORMAT);
    },
    unserialize(
      property: keyof DateTimeConfiguration<object>,
      data: string,
      options: DateTimeConfiguration<object>,
    ): SerializeTypes {
      if (property !== "native_value") {
        return data as SerializeTypes;
      }
      const ref = dayjs(data).startOf("day");
      switch (options.date_type) {
        case "dayjs": {
          return ref;
        }
        case "date": {
          return ref.toDate();
        }
        default: {
          return ref.format(FORMAT) as SynapseDateFormat;
        }
      }
    },
    validate(
      current: DateConfiguration<object>,
      key: keyof DateConfiguration<object>,
      newValue: unknown,
    ) {
      if (key !== "native_value") {
        return true;
      }
      const incoming = dayjs(newValue as ConfigType);
      if (incoming.isValid()) {
        return true;
      }
      logger.error({ expected: current.date_type || "ISO8601", newValue }, "unknown value type");
      throw new SynapseEntityException(context, "SET_INVALID_DATE", `Received invalid date format`);
    },
  });

  // #MARK: builder
  return function <
    PARAMS extends DateParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      DateConfiguration<object>
    >,
  >({
    managed = true,
    ...options
  }: AddEntityOptions<
    DateConfiguration<DATA>,
    DateEvents,
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

    type DynamicCallbacks = BuildCallbacks<DateEvents<CallbackType<PARAMS["date_type"]>>>;
    type TypedVirtualDate = Omit<typeof entity, keyof DynamicCallbacks | "native_value"> &
      DynamicCallbacks & { native_value: CallbackType<PARAMS["date_type"]> };

    return entity as TypedVirtualDate;
  };
}
