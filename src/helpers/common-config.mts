import { CronExpression, is, TBlackHole, TContext } from "@digital-alchemy/core";
import {
  ByIdProxy,
  ENTITY_STATE,
  PICK_ENTITY,
  RemoveCallback,
  TEntityUpdateCallback,
} from "@digital-alchemy/hass";
import { CamelCase } from "type-fest";

import { CreateRemovableCallback, TEventMap } from "./base-domain.mts";
import { TSynapseEntityStorage } from "./storage.mts";
import { TSynapseDeviceId } from "./utility.mts";

export type EntityConfigCommon<
  ATTRIBUTES extends object,
  LOCALS extends object,
  DATA extends object,
> = {
  /**
   * Use a different device to register this entity
   */
  device_id?: TSynapseDeviceId;
  /**
   * Attempt to create the entity id using this string
   *
   * `binary_sensor.{suggested id}`
   *
   * Home assistant _may_ append numbers to the end in case of object_id conflicts where `unique_id` isn't the same.
   *
   * > **NOTE:** Default value based on `name`
   */
  suggested_object_id?: string;
  /**
   * Provide your own unique id for this entity
   *
   * This ID uniquely identifies the entity, through `entity_id` renames
   */
  unique_id?: string;
  disabled?: SettableConfiguration<boolean, DATA>;
  icon?: SettableConfiguration<string, DATA>;
  /**
   * An entity with a category will:
   * - Not be exposed to cloud, Alexa, or Google Assistant components
   * - Not be included in indirect service calls to devices or areas
   *
   * **Config**: An entity which allows changing the configuration of a device.
   *
   * **Diagnostic**: An entity exposing some configuration parameter, or diagnostics of a device.
   */
  entity_category?: "config" | "diagnostic";
  /**
   * Default name to provide for the entity
   */
  name: string;
  translation_key?: string;
  /**
   * passed through as extra entity attributes to home assistant
   *
   * > consider creating sensor entities instead
   */
  attributes?: ATTRIBUTES;
  /**
   * local state data, not sent to home assistant
   *
   * can be used as a sqlite backed cache for entity specific data
   */
  locals?: LOCALS;
  /**
   * Automatically trigger reactive config updates in response to updates from these entities
   *
   * List gets merged with `onUpdate` array in the configs, is convenient shorthand
   */
  bind?: Updatable<DATA>[];
};

export const isCommonConfigKey = <ATTRIBUTES extends object, LOCALS extends object>(
  key: string,
): key is keyof EntityConfigCommon<ATTRIBUTES, LOCALS, object> => COMMON_CONFIG_KEYS.has(key);

export type SettableConfiguration<TYPE extends unknown, DATA extends object> =
  /**
   * Straight provide the value.
   * If this changes in the definition (hard coded value usually), then the entity config will be reset
   *
   * This option can be used with assignments
   *
   * ```typescript
   * entity.field = new_value;
   * ```
   */
  | TYPE
  // Verbose form
  | ReactiveConfig<TYPE, DATA>
  // Equiv of the `current` for the verbose reactive config
  // If you don't need the other options (or prefer bind), this works great 👍
  | ((data: DATA) => TYPE);

export type Updatable<DATA extends object> = {
  onUpdate: (callback: (data: DATA) => TBlackHole) => void;
};

/**
 * > **NOTE**: `onUpdate` list is merged with the `bind` array that is provided to the entity
 * ```typescript
 * {
 *   icon: {
 *     current() {
 *       return someLogic ? "mdi:cookie-clock" : "mdi:cookie-alert-outline";
 *     },
 *     onUpdate: [hassEntityReference, synapseEntityReference],
 *     // every 30 seconds by default
 *     schedule: CronExpression.EVERY_SECOND,
 *   },
 * }
 * ```
 */
export type ReactiveConfig<TYPE extends unknown = unknown, DATA extends object = object> = {
  /**
   * Update immediately in response to entity updates
   */
  onUpdate?: Updatable<DATA>[];
  /**
   * Every 30s by default
   */
  schedule?: CronExpression | string;
  /**
   * Calculate current value
   */
  current(data: DATA): TYPE;
};

export const isShortReactiveConfig = (key: string, value: unknown): value is ReactiveConfig =>
  is.function(value) && key !== "attributes" && !NO_LIVE_UPDATE.has(key);

export const isReactiveConfig = (key: string, value: unknown): value is ReactiveConfig =>
  is.object(value) &&
  is.function((value as { current: () => void }).current) &&
  key !== "attributes" &&
  !NO_LIVE_UPDATE.has(key);

export const NO_LIVE_UPDATE = new Set<string>([
  "device_class",
  "device_id",
  "entity_category",
  "managed",
  "name",
  "suggested_object_id",
  "translation_key",
  "unique_id",
]);

export const COMMON_CONFIG_KEYS = new Set([
  "attributes",
  "device_id",
  "entity_category",
  "icon",
  "disabled",
  "name",
  "suggested_object_id",
  "translation_key",
  "unique_id",
]);

export type NON_SETTABLE =
  | "managed"
  | "suggested_object_id"
  | "unique_id"
  | "device_id"
  | "device_class"
  | "translation_key"
  | "entity_category";

export type NonReactive<CONFIGURATION extends object> = {
  [KEY in Extract<keyof CONFIGURATION, string>]: CONFIGURATION[KEY] extends SettableConfiguration<
    infer TYPE,
    object
  >
    ? TYPE
    : CONFIGURATION[KEY];
};

export type CommonMethods<
  CONFIGURATION extends object,
  LOCALS extends object,
  DATA extends object,
> = {
  /**
   * Look up the actual entity_id that is mapped to this entity by unique_id
   */
  entity_id: PICK_ENTITY;
  /**
   * retrieve the related hass entity reference
   *
   * note: requires that entity actually exist in home assistant to be valid (does a lookup)
   */
  getEntity: () => ByIdProxy<PICK_ENTITY>;
  /**
   * Run callback once, for next update
   */
  once: <ENTITY extends PICK_ENTITY>(callback: TEntityUpdateCallback<ENTITY>) => RemoveCallback;
  /**
   * Will resolve with the next state of the next value. No time limit
   */
  nextState: <ENTITY extends PICK_ENTITY>(timeoutMs?: number) => Promise<ENTITY_STATE<ENTITY>>;
  /**
   * Will resolve when state
   */
  waitForState: <ENTITY extends PICK_ENTITY>(
    state: string | number,
    timeoutMs?: number,
  ) => Promise<ENTITY_STATE<ENTITY>>;
  /**
   * triggered by the hass entity emitting a state change, requires full round trip:
   *
   * 0) trigger
   * 1) you change something
   * 2) synapse sends change to extension
   * 3) extension notifies hass
   * 4) hass emits update event
   * 5) this callback gets triggered
   */
  onUpdate(callback: TEntityUpdateCallback<PICK_ENTITY>): RemoveCallback;
  /**
   * @internal
   */
  storage: TSynapseEntityStorage<CONFIGURATION & EntityConfigCommon<object, LOCALS, DATA>>;
  /**
   * add a listener that can be removed with the removeAllListeners call
   *
   * for use by other libraries
   */
  addListener: (remove: RemoveCallback) => void;
  /**
   * Remove all runtime resources related to this particular entity
   *
   * - does not remove entity from database
   * - does not emit anything to home assistant
   */
  removeAllListeners: () => void;
  /**
   * - removes entity from local database
   * - attempts to remove entity from integration
   */
  purge: () => void;
};

/**
 * Synapse proxy
 */
type ProxyBase<
  CONFIGURATION extends object,
  EVENT_MAP extends TEventMap,
  ATTRIBUTES extends object,
  LOCALS extends object,
  DATA extends object,
> = CommonMethods<CONFIGURATION, LOCALS, DATA> &
  NonReactive<CONFIGURATION> &
  BuildCallbacks<EVENT_MAP> &
  EntityConfigCommon<ATTRIBUTES, LOCALS, DATA> & {
    /**
     * @internal
     *
     * duplicate the entity proxy, used for management of listeners
     */
    child: (context: TContext) => ProxyBase<CONFIGURATION, EVENT_MAP, ATTRIBUTES, LOCALS, DATA>;
  };

/**
 * The combination of all properties that went in, minus those that don't play well with runtime updates
 *
 * That is also enforced
 */
export type SynapseEntityProxy<
  CONFIGURATION extends object,
  EVENT_MAP extends TEventMap,
  ATTRIBUTES extends object,
  LOCALS extends object,
  DATA extends object,
  PROXY = ProxyBase<CONFIGURATION, EVENT_MAP, ATTRIBUTES, LOCALS, DATA>,
> = Omit<PROXY, Extract<keyof PROXY, NON_SETTABLE>>;

export type BuildCallbacks<EVENT_MAP extends TEventMap> = {
  [EVENT_NAME in Extract<
    keyof EVENT_MAP,
    string
  > as CamelCase<`on-${EVENT_NAME}`>]: CreateRemovableCallback<EVENT_MAP[EVENT_NAME]>;
};
export type GenericSynapseEntity<DATA extends object = object> = SynapseEntityProxy<
  object,
  TEventMap,
  object,
  object,
  DATA
>;
