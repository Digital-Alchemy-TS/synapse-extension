import { TServiceParams } from "@digital-alchemy/core";

export function SynapseLocalsService({ synapse, logger, internal, event }: TServiceParams) {
  const { is } = internal.utils;

  // #MARK: updateLocal
  async function updateLocal(unique_id: string, key: string, content: unknown) {
    logger.trace({ key, unique_id }, "updateLocal");

    if (is.undefined(content)) {
      logger.debug({ key, unique_id }, `delete local (value {undefined})`);
      await synapse.sqlite.deleteLocal(unique_id, key);
      return;
    }

    logger.trace({ key, unique_id }, "update local");
    await synapse.sqlite.updateLocal(unique_id, key, content);
  }

  // #MARK: loadLocals
  /**
   * locals are only loaded when they are first utilized for a particular entity
   *
   * allows for more performant cold boots
   */
  async function loadLocals(unique_id: string) {
    if (!internal.boot.completedLifecycleEvents.has("PostConfig")) {
      logger.warn("cannot load locals before [PostConfig]");
      return undefined;
    }
    logger.trace({ unique_id }, "initial load of locals");
    return await synapse.sqlite.loadLocals(unique_id);
  }

  // #MARK: deleteLocal
  async function deleteLocal(unique_id: string, key: string) {
    logger.debug({ key, unique_id }, `delete local (value undefined)`);
    await synapse.sqlite.deleteLocal(unique_id, key);
  }

  // #MARK: deleteLocalsByUniqueId
  async function deleteLocalsByUniqueId(unique_id: string) {
    logger.debug({ unique_id }, "delete all locals");
    await synapse.sqlite.deleteLocalsByUniqueId(unique_id);
  }

  // #MARK: localsProxy
  function localsProxy<LOCALS extends object>(unique_id: string, defaults: LOCALS) {
    let loaded = false;
    let data = { ...defaults } as LOCALS;
    const loadedData = new Map<string, unknown>();

    // Create the proxy for locals
    const proxy = new Proxy(data, {
      deleteProperty(target, property: string) {
        // Remove from target
        delete (target as Record<string, unknown>)[property];

        // Remove from loaded data
        loadedData.delete(property);

        // Delete from database
        if (internal.boot.completedLifecycleEvents.has("PostConfig")) {
          void deleteLocal(unique_id, property);
        }

        return true;
      },

      get(target, property: string) {
        // Load data on first access if not loaded yet
        if (!loaded && internal.boot.completedLifecycleEvents.has("PostConfig")) {
          void loadLocals(unique_id).then(locals => {
            if (locals) {
              loadedData.clear();
              locals.forEach((value, key) => {
                loadedData.set(key, value);
                if (key in target) {
                  (target as Record<string, unknown>)[key] = value;
                }
              });
            }
            loaded = true;
          });
        }

        // Return loaded data if available, otherwise return default
        if (loadedData.has(property)) {
          return loadedData.get(property);
        }
        return (target as Record<string, unknown>)[property];
      },

      has(target, property: string) {
        return loadedData.has(property) || property in target;
      },

      ownKeys(target) {
        const keys = new Set<string>();
        // Add default keys
        Object.keys(target).forEach(key => keys.add(key));
        // Add loaded keys
        loadedData.forEach((_, key) => keys.add(key));
        return Array.from(keys);
      },

      set(target, property: string, value: unknown) {
        // Update the target
        (target as Record<string, unknown>)[property] = value;

        // Store in loaded data
        loadedData.set(property, value);

        // Persist to database
        if (internal.boot.completedLifecycleEvents.has("PostConfig")) {
          void updateLocal(unique_id, property, value);
        }

        return true;
      },
    });

    return {
      proxy,
      replace(newValue: LOCALS) {
        loadedData.clear();
        data = { ...newValue } as LOCALS;
        if (internal.boot.completedLifecycleEvents.has("PostConfig")) {
          // Clear existing and set new values
          void deleteLocalsByUniqueId(unique_id).then(() => {
            Object.entries(newValue).forEach(([key, value]) => {
              if (value !== undefined) {
                void updateLocal(unique_id, key, value);
              }
            });
          });
        }
      },
      reset() {
        loadedData.clear();
        data = { ...defaults } as LOCALS;
        if (internal.boot.completedLifecycleEvents.has("PostConfig")) {
          void deleteLocalsByUniqueId(unique_id);
        }
      },
    };
  }

  return {
    deleteLocal,
    deleteLocalsByUniqueId,
    loadLocals,
    localsProxy,
    updateLocal,
  };
}
