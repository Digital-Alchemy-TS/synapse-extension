import { TServiceParams } from "@digital-alchemy/core";

import {
  DELETE_LOCALS_BY_UNIQUE_ID_QUERY,
  DELETE_LOCALS_QUERY,
  ENTITY_LOCALS_UPSERT,
  HomeAssistantEntityLocalRow,
  SELECT_LOCALS_QUERY,
  TSynapseId,
} from "../helpers/index.mts";
import { prefix } from "./sqlite.service.mts";

export function SynapseLocalsService({ synapse, logger, internal, event }: TServiceParams) {
  const { is } = internal.utils;
  // #MARK: updateLocal
  function updateLocal(unique_id: TSynapseId, key: string, content: unknown) {
    const database = synapse.sqlite.getDatabase();
    logger.trace({ key, unique_id }, "updateLocal");

    if (is.undefined(content)) {
      logger.debug({ key, unique_id }, `delete local (value {undefined})`);
      database.prepare(DELETE_LOCALS_QUERY).run([unique_id, key]);
      return;
    }

    const value_json = JSON.stringify(content);
    const last_modified = new Date().toISOString();
    const param = prefix({
      key,
      last_modified,
      unique_id,
      value_json,
    });
    logger.trace({ param }, "update local");

    database.prepare(ENTITY_LOCALS_UPSERT).run(param);
  }

  // #MARK: loadLocals
  /**
   * locals are only loaded when they are first utilized for a particular entity
   *
   * allows for more performant cold boots
   */
  function loadLocals(unique_id: TSynapseId) {
    if (!internal.boot.completedLifecycleEvents.has("PostConfig")) {
      logger.warn("cannot load locals before [PostConfig]");
      return undefined;
    }
    logger.trace({ unique_id }, "initial load of locals");
    const database = synapse.sqlite.getDatabase();

    const locals = database
      .prepare<[TSynapseId], HomeAssistantEntityLocalRow>(SELECT_LOCALS_QUERY)
      .all(unique_id);

    return new Map<string, unknown>(locals.map(i => [i.key, JSON.parse(i.value_json)]));
  }

  // #MARK: localsProxy
  function localsProxy<LOCALS extends object>(unique_id: TSynapseId, defaults: LOCALS) {
    logger.trace({ unique_id }, "building locals proxy");
    let locals: Map<string, unknown>;

    const proxyItem = { ...defaults };
    type ProxyKey = keyof typeof proxy;
    const proxy = new Proxy(proxyItem as LOCALS, {
      // * delete entity.locals.thing
      deleteProperty(_, key: string) {
        locals ??= loadLocals(unique_id);
        if (!locals) {
          return false;
        }
        if (!locals.has(key)) {
          return true;
        }
        logger.trace({ key, unique_id }, "delete local");
        const database = synapse.sqlite.getDatabase();
        database.prepare(DELETE_LOCALS_QUERY).run([unique_id, key]);
        locals.delete(key);
        if (!(key in defaults)) {
          delete proxyItem[key as keyof typeof proxyItem];
        }
        return true;
      },
      get(_, property: string) {
        locals ??= loadLocals(unique_id);
        if (!locals) {
          return defaults[property as keyof LOCALS];
        }
        if (locals.has(property)) {
          return locals.get(property);
        }
        logger.trace({ unique_id }, `using code default for [%s]`, property);
        return defaults[property as keyof LOCALS];
      },

      // * "thing" in entity.locals
      has(_, property: string) {
        locals ??= loadLocals(unique_id);
        if (property in defaults) {
          return true;
        }
        return Boolean(locals?.has(property));
      },

      // * Object.keys(entity.locals)
      ownKeys() {
        locals ??= loadLocals(unique_id);
        if (!locals) {
          return Object.keys(defaults);
        }
        return is.unique([...Object.keys(defaults), ...locals.keys()]);
      },
      set(_, property: string, value) {
        locals ??= loadLocals(unique_id);
        if (!locals) {
          logger.trace("ignoring set attempt, locals not available");
          return false;
        }
        if (is.equal(locals.get(property), value)) {
          logger.trace({ property, unique_id }, `value didn't change, not saving`);
          return true;
        }
        proxyItem[property as keyof typeof proxyItem] = value;
        logger.debug({ unique_id }, `updating [%s]`, property);
        synapse.locals.updateLocal(unique_id, property, value);
        locals.set(property, value);
        event.emit(unique_id);
        return true;
      },
    });

    return {
      proxy,
      replace: (data: LOCALS) => {
        locals ??= loadLocals(unique_id);
        if (!locals) {
          logger.trace("ignoring replace attempt, locals not available");
          return false;
        }
        logger.debug("replace locals");
        const incoming = Object.keys(data);
        const current = is.unique([...Object.keys(defaults), ...locals.keys()]);

        current.filter(i => !incoming.includes(i)).forEach(key => delete proxy[key as ProxyKey]);
        Object.entries(data).forEach(([key, value]) => (proxy[key as ProxyKey] = value));
        return true;
      },
      // * delete entity.locals
      reset: () => {
        logger.warn({ unique_id }, "reset locals");
        const database = synapse.sqlite.getDatabase();
        database.prepare(DELETE_LOCALS_BY_UNIQUE_ID_QUERY).run([unique_id]);
        locals = new Map();
      },
    };
  }

  return { localsProxy, updateLocal };
}
