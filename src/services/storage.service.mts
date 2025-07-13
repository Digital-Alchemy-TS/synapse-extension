import {
  CronExpression,
  debounce,
  DOWN,
  HALF,
  InternalError,
  SECOND,
  TServiceParams,
  UP,
} from "@digital-alchemy/core";
import { TRawDomains, TUniqueId } from "@digital-alchemy/hass";

import {
  AddStateOptions,
  COMMON_CONFIG_KEYS,
  EntityConfigCommon,
  generateHash,
  isCommonConfigKey,
  isReactiveConfig,
  NO_LIVE_UPDATE,
  ReactiveConfig,
  TSynapseEntityStorage,
  TSynapseId,
} from "../helpers/index.mts";

const RESYNC_DELAY = HALF * SECOND;

/**
 * Storage entries are generated on a 1-1 basis with entities using `add`
 */
export function StorageService({
  logger,
  context,
  lifecycle,
  hass,
  synapse,
  event,
  scheduler,
  internal,
}: TServiceParams) {
  const { is } = internal.utils;
  const registry = new Map<TSynapseId, TSynapseEntityStorage>();
  const domain_lookup = new Map<string, TRawDomains>();

  hass.events.onEntityRegistryUpdate(async () => {
    await debounce("synapse_storage", RESYNC_DELAY);
    logger.info("entity storage resync");
    for (const [unique_id] of registry) {
      await synapse.sqlite.update(unique_id, registry.get(unique_id).export());
    }
  });

  /**
   * Convert the registry into the expected data format for sending to Home Assistant
   */
  // #MARK: dump
  function dump() {
    const list = [...registry.keys()];
    const out = {} as Record<TRawDomains, object[]>;
    list.forEach(i => {
      const storage = registry.get(i);
      const section = domain_lookup.get(i);
      out[section] ??= [];
      out[section].push(storage.export());
    });
    return out;
  }

  // #MARK: add
  /**
   *
   */
  function add<
    LOCALS extends object,
    ATTRIBUTES extends object,
    CONFIGURATION extends EntityConfigCommon<ATTRIBUTES, LOCALS, DATA>,
    DATA extends object,
  >({
    entity,
    load_config_keys,
    domain,
    bind = [],
    serialize,
  }: AddStateOptions<ATTRIBUTES, LOCALS, CONFIGURATION, DATA>) {
    if (registry.has(entity.unique_id as TSynapseId)) {
      throw new InternalError(context, `ENTITY_COLLISION`, `${domain} registry already id`);
    }
    domain_lookup.set(entity.unique_id, domain);
    let initialized = false;
    type ValueData = Record<keyof CONFIGURATION, unknown>;
    type LoadKeys = keyof EntityConfigCommon<ATTRIBUTES, LOCALS, DATA>;
    let CURRENT_VALUE = {} as ValueData;
    const load = [...load_config_keys, ...COMMON_CONFIG_KEYS.values()] as LoadKeys[];

    // run through the import
    load.forEach(key => {
      let value = entity[key];
      if (!NO_LIVE_UPDATE.has(key) && is.function(value)) {
        // @ts-expect-error fixme
        value = { current: value } as unknown;
      }
      if (isReactiveConfig(key, value)) {
        registerReactiveConfig(key, value);
        return;
      }
      CURRENT_VALUE[key] = value;
    });

    // #MARK: createSettableConfig
    /**
     * Handle the the logic for the reactive
     */
    function registerReactiveConfig(key: keyof CONFIGURATION, config: ReactiveConfig) {
      // keep this one local to make sure the correct listener gets gc'd
      // never can be sure when property refs might change (tin foil hat)
      const unique_id = entity.unique_id;

      /**
       * update handler
       */
      async function updateSettableConfig() {
        const current_value = storage.get(key);
        const known = synapse.generator.knownEntities.get(unique_id);
        // console.log({ known });
        const new_value = config.current(known) as CONFIGURATION[typeof key];
        if (new_value === current_value) {
          logger.trace({ key, unique_id: entity.unique_id }, "ignoring noop");
          return;
        }
        logger.trace(
          { key, name: updateSettableConfig, unique_id: entity.unique_id },
          `setting new value`,
        );
        await storage.set(key, new_value);
      }

      // Check periodically to ensure accuracy with time based things
      scheduler.cron({
        exec: updateSettableConfig,
        schedule: config.schedule || CronExpression.EVERY_30_SECONDS,
      });

      const onUpdate = [...bind, ...(config.onUpdate ?? [])];
      // Track reference entities
      if (!is.empty(onUpdate)) {
        onUpdate.forEach(entity => entity.onUpdate(updateSettableConfig));
      }
      lifecycle.onReady(() => updateSettableConfig());
      event.on(unique_id, updateSettableConfig);
      setImmediate(() => updateSettableConfig());
      return internal.removeFn(() => {
        event.removeListener(unique_id, updateSettableConfig);
      });
    }

    // #MARK: storage
    const storage = {
      export: () => {
        const keys = Object.keys(CURRENT_VALUE) as Extract<keyof typeof CURRENT_VALUE, string>[];
        return Object.fromEntries(
          keys.map(i => {
            if (serialize) {
              // @ts-expect-error don't care
              return [i, serialize(i, CURRENT_VALUE[i], undefined)];
            }
            return [i, CURRENT_VALUE[i]];
          }),
        ) as ValueData;
      },
      get: key => CURRENT_VALUE[key],
      isStored: (key: string): key is Extract<keyof CONFIGURATION, string> =>
        isCommonConfigKey(key) || load_config_keys.includes(key),
      keys: () => load,
      purge() {
        logger.warn("you should report this... I think");
      },
      set: async (key: Extract<keyof CONFIGURATION, string>, value) => {
        const unique_id = entity.unique_id as TSynapseId;
        if (NO_LIVE_UPDATE.has(key)) {
          throw new InternalError(context, "NO_LIVE_UPDATE", `${key} cannot be updated at runtime`);
        }
        CURRENT_VALUE[key] = value;
        if (initialized) {
          logger.trace({ key, unique_id }, "update locals");
          await synapse.sqlite.update(unique_id, registry.get(unique_id).export());
          if (hass.socket.connectionState === "connected") {
            setImmediate(async () => await synapse.socket.send(unique_id, CURRENT_VALUE));
          }
        }
      },
      unique_id: entity.unique_id,
    } as TSynapseEntityStorage<CONFIGURATION>;
    registry.set(entity.unique_id as TSynapseId, storage as unknown as TSynapseEntityStorage);

    // * value loading
    lifecycle.onReady(async function onReady() {
      // - identify id
      const unique_id = entity.unique_id as TSynapseId;

      // - ??
      const data = await synapse.sqlite.load(unique_id, CURRENT_VALUE);
      if (is.empty(data?.state_json)) {
        initialized = true;
        logger.debug({ unique_id }, "initial create entity row");
        await synapse.sqlite.update(unique_id, registry.get(unique_id).export());
        return;
      }

      // - load previous value
      logger.debug({ entity_id: data.entity_id, name: onReady }, `importing value from db`);
      CURRENT_VALUE = JSON.parse(data.state_json);
      initialized = true;
    });

    // * done
    return storage;
  }

  return {
    add,
    dump,
    find: <CONFIGURATION extends object>(id: TSynapseId | TUniqueId) =>
      registry.get(id as TSynapseId) as unknown as TSynapseEntityStorage<CONFIGURATION>,
    hash: () =>
      generateHash(
        [...registry.keys(), ...synapse.device.idList()]
          .toSorted((a, b) => (a > b ? UP : DOWN))
          .join("|"),
      ),
  };
}
