import { SINGLE, START, TAnyFunction, TContext, TServiceParams } from "@digital-alchemy/core";
import {
  ANY_ENTITY,
  ByIdProxy,
  ENTITY_STATE,
  HassUniqueIdMapping,
  PICK_ENTITY,
  RemoveCallback,
  TUniqueId,
} from "@digital-alchemy/hass";

import {
  AddEntityOptions,
  BaseEvent,
  CreateRemovableCallback,
  DomainGeneratorOptions,
  EntityConfigCommon,
  formatObjectId,
  generateHash,
  GenericSynapseEntity,
  RemovableCallback,
  SynapseEntityProxy,
  TEventMap,
  TSynapseId,
} from "../helpers/index.mts";

export function DomainGeneratorService({
  logger,
  internal,
  synapse,
  event,
  hass,
  context,
  config,
}: TServiceParams) {
  const { is } = internal.utils;
  // #MARK: removableListener
  function removableListener<DATA extends object>(
    eventName: string,
    callback: RemovableCallback<DATA>,
  ) {
    const remove = () => event.removeListener(eventName, exec);
    const exec = async (data: DATA) =>
      await internal.safeExec(async () => await callback(data, remove));
    event.on(eventName, exec);
    return internal.removeFn(remove);
  }
  const getIdentifier = () => internal.boot.application.name;
  const registeredEvents = new Set<string>();
  const knownEntities = new Map<string, GenericSynapseEntity>();

  // #MARK: busTransfer
  function busTransfer<EVENT_MAP extends TEventMap>(
    bus_events: Extract<keyof EVENT_MAP, string>[],
  ) {
    bus_events.forEach(name => {
      // some domains duplicate others
      if (registeredEvents.has(name)) {
        return;
      }
      logger.trace({ name }, "set up bus transfer");
      registeredEvents.add(name);
      hass.socket.onEvent({
        context,
        event: [config.synapse.EVENT_NAMESPACE, name, getIdentifier()].join("/"),
        exec: ({ data }: BaseEvent) => {
          logger.trace({ data, name }, `receive`);
          const target = `synapse/${name}/${data.unique_id}`;
          event.emit(target, data);
        },
      });
    });
  }

  // #MARK: create
  function create<
    CONFIGURATION extends object,
    EVENT_MAP extends TEventMap,
    SERIALIZE_TYPES extends unknown = unknown,
  >(options: DomainGeneratorOptions<CONFIGURATION, EVENT_MAP, SERIALIZE_TYPES>) {
    const { domain, context, bus_events = [], load_config_keys = [], ...extra } = options;
    logger.debug({ bus_events, context }, "registering domain [%s]", domain);

    busTransfer(bus_events);

    // #MARK: addEntity
    function addEntity<ATTRIBUTES extends object, LOCALS extends object, DATA extends object>(
      entity: AddEntityOptions<CONFIGURATION, EVENT_MAP, ATTRIBUTES, LOCALS, DATA>,
      clone = false,
    ) {
      // * defaults
      // - unique_id - required for comms
      entity.unique_id = is.empty(entity.unique_id)
        ? generateHash(`${getIdentifier()}:${entity.suggested_object_id || entity.name}`)
        : entity.unique_id;
      // - suggested_object_id - required on python side due to the way the code is set up
      entity.suggested_object_id ??= formatObjectId(entity.name);

      const unique_id = entity.unique_id as TUniqueId;
      const currentProxy = knownEntities.get(unique_id);

      if (currentProxy && !clone) {
        logger.trace({ clone, currentProxy }, `returning existing proxy`);
        return currentProxy as unknown as SynapseEntityProxy<
          CONFIGURATION,
          EVENT_MAP,
          ATTRIBUTES,
          LOCALS,
          DATA
        >;
      } else if (currentProxy) {
        logger.debug({ unique_id }, `creating clone`);
      }

      type mergedConfig = CONFIGURATION & EntityConfigCommon<ATTRIBUTES, LOCALS, DATA>;

      // * initialize storage
      const storage = clone
        ? synapse.storage.find<mergedConfig>(unique_id)
        : synapse.storage.add<LOCALS, ATTRIBUTES, mergedConfig, DATA>({
            bind: entity.bind,
            domain,
            entity,
            load_config_keys,
            // @ts-expect-error don't care
            serialize: "serialize" in extra ? extra.serialize : undefined,
            // @ts-expect-error don't care
            unserialize: "unserialize" in extra ? extra.unserialize : undefined,
          });

      // * map bus events
      bus_events.forEach(bus_event => {
        if (is.undefined(entity[bus_event])) {
          return;
        }
        logger.trace({ bus_event, context, name: entity.name }, `static attach`);
        synapse.generator.removableListener(`synapse/${bus_event}/${unique_id}`, entity[bus_event]);
      });

      // * build dynamic listeners
      const dynamicAttach = Object.fromEntries(
        bus_events.map(name => [
          `on${name
            .split("_")
            .map(i => i.charAt(START).toUpperCase() + i.slice(SINGLE))
            .join("")}`,
          ((callback: RemovableCallback) =>
            synapse.generator.removableListener(
              `synapse/${name}/${unique_id}`,
              callback,
            )) as CreateRemovableCallback,
        ]),
      );

      // * pre-create proxy for locals
      // (doesn't load data immediately)
      const locals = synapse.locals.localsProxy(unique_id as TSynapseId, entity.locals ?? {});

      const keys = is.unique([
        "locals",
        "getEntity",
        "storage",
        "onUpdate",
        ...Object.keys(dynamicAttach),
        ...storage.keys(),
      ]);

      // ? adding the keys here makes ownKeys & has work
      const thing = Object.fromEntries(keys.map(i => [i, true])) as SynapseEntityProxy<
        CONFIGURATION,
        EVENT_MAP,
        ATTRIBUTES,
        LOCALS,
        DATA
      >;

      const listeners = new Set<() => void>();
      const entityRefs = new Map<PICK_ENTITY, ByIdProxy<PICK_ENTITY>>();

      function getEntity() {
        const id = hass.idBy.unique_id(unique_id);
        if (!id) {
          logger.warn(
            { name: entity.name, unique_id },
            `cannot find entity (is it loaded by integration?)`,
          );
          return undefined;
        }
        const current = entityRefs.get(id);
        if (current) {
          logger.trace({ id }, "entity ref from cache");
          return current;
        }
        if (!is.empty(entityRefs)) {
          logger.warn({ existing: [...entityRefs.keys()], new_id: id }, `leaking reference`);
        }
        logger.trace({ id }, "loading entity ref");
        const ref = hass.refBy.id(id);
        entityRefs.set(id, ref);
        return ref;
      }

      // #MARK: entity proxy
      const outProxy = new Proxy(thing, {
        deleteProperty(_, property: string) {
          if (property === "locals") {
            logger.debug({ unique_id }, "delete all locals");
            locals.reset();
            return true;
          }
          logger.warn({ property }, "cannot delete entity property");
          return false;
        },

        // #MARK: get
        get(_, property: Extract<keyof CONFIGURATION, string>) {
          if (!is.undefined(dynamicAttach[property])) {
            return dynamicAttach[property];
          }
          if (storage.isStored(property)) {
            const out = storage.get(property);
            return "unserialize" in extra
              ? extra.unserialize(property, out as string, entity)
              : out;
          }
          switch (property) {
            // #MARK: locals
            case "locals": {
              return locals.proxy;
            }

            // #MARK: entity_id
            case "entity_id": {
              return hass.idBy.unique_id(unique_id);
            }

            // #MARK: getEntity
            case "getEntity": {
              return getEntity;
            }

            // #MARK: child
            case "child": {
              return function (context: TContext) {
                logger.trace({ unique_id }, "generate child");
                const child = addEntity(
                  {
                    // copy input data
                    ...entity,
                    // override context
                    context,
                    // remove any hard coded events
                    ...Object.fromEntries(bus_events.map((i): [string, unknown] => [i, undefined])),
                  },
                  true,
                ) as unknown as GenericSynapseEntity;
                const remove = internal.removeFn(() => {
                  logger.trace({ unique_id }, "cleanup child");
                  listeners.delete(remove);
                  child.removeAllListeners();
                });
                child.addListener(internal.removeFn(() => listeners.delete(remove)));
                listeners.add(remove);
                return child;
              };
            }

            // #MARK: storage
            case "storage": {
              return storage;
            }

            // #MARK: addListener
            case "addListener": {
              return function (listener: RemoveCallback) {
                logger.trace({ unique_id }, "add listener");
                const rm = () => {
                  logger.trace("removing listener");
                  listener();
                  listeners.delete(rm);
                };
                listeners.add(rm);
              };
            }

            // #MARK: removeAllListeners
            case "removeAllListeners": {
              return function () {
                logger.debug({ unique_id }, "removeAllListeners");
                // remove will delete from set
                listeners.forEach(remove => remove());
              };
            }

            // #MARK: purge
            case "purge": {
              return function () {
                logger.info({ unique_id }, "purge");
                listeners.forEach(remove => remove());
                entityRefs.forEach((entity, key) => {
                  entity.removeAllListeners();
                  entityRefs.delete(key);
                });
                storage.purge();
              };
            }

            // #MARK: onUpdate
            case "onUpdate": {
              type ENTITY_ID = Extract<HassUniqueIdMapping[typeof unique_id], ANY_ENTITY>;
              return function (callback: TAnyFunction) {
                logger.trace({ unique_id }, "attach onUpdate");
                const removableCallback = async (
                  new_state: ENTITY_STATE<ENTITY_ID>,
                  old_state: ENTITY_STATE<ENTITY_ID>,
                ) => await internal.safeExec(async () => callback(new_state, old_state, remove));

                function remove() {
                  logger.trace({ unique_id }, "remove onUpdate");
                  event.removeListener(unique_id, removableCallback);
                  listeners.delete(remove);
                }

                listeners.add(remove);
                event.on(unique_id, removableCallback);
                return internal.removeFn(remove);
              };
            }

            // #MARK: nextState
            case "nextState": {
              return function (timeoutMs?: number) {
                logger.trace({ timeoutMs, unique_id }, "nextState");
                return getEntity()?.nextState(timeoutMs);
              };
            }

            // #MARK: waitForState
            case "waitForState": {
              return function (state: string | number, timeoutMs?: number) {
                logger.trace({ state, timeoutMs, unique_id }, "waitForState");
                return getEntity()?.waitForState(state, timeoutMs);
              };
            }
          }
          return undefined;
        },

        // #MARK: has
        has(_, property: string) {
          return keys.includes(property);
        },

        // #MARK: ownKeys
        ownKeys() {
          return keys;
        },

        // #MARK: set
        set(_, property: Extract<keyof CONFIGURATION, string>, newValue) {
          // * replace all locals
          if (property === "locals") {
            logger.trace({ newValue }, "replace locals");
            locals.replace(newValue);
            return false;
          }
          // * manage entity config properties
          if (storage.isStored(property)) {
            // if the domain provides a serialization process, do that before storing
            try {
              if ("validate" in extra) {
                extra.validate(entity, property, newValue);
              }
              if ("serialize" in extra) {
                newValue = extra.serialize(property, newValue, entity);
              }
            } catch (error) {
              logger.error(
                {
                  context: entity.context,
                  error,
                  name: entity.name,
                  newValue,
                  property,
                  unique_id: entity.unique_id,
                },
                "set failed",
              );
              return false;
            }
            logger.trace({ property }, "updating storage");
            void storage.set(property, newValue);
            return true;
          }
          // * nothing else is settable right now
          return false;
        },
      });
      knownEntities.set(unique_id, outProxy as unknown as GenericSynapseEntity);
      return outProxy;
    }

    return { addEntity };
  }

  return {
    create,
    knownEntities,
    removableListener,
  };
}
