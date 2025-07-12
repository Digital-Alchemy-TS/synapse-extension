import { is, TServiceParams } from "@digital-alchemy/core";
import SQLiteDriver, { Database } from "better-sqlite3";

import {
  ENTITY_CREATE,
  ENTITY_UPSERT,
  HomeAssistantEntityRow,
  LOCALS_CREATE,
  SELECT_QUERY,
  TSynapseId,
} from "../helpers/index.mts";

export type SynapseSqliteDriver = typeof SQLiteDriver;

type SynapseSqlite = {
  getDatabase: () => Database;
  load: (unique_id: TSynapseId, defaults: object) => HomeAssistantEntityRow;
  update: (unique_id: TSynapseId, content: object, defaults?: object) => void;
};

const isBun = !is.empty(process.versions.bun);
async function getDriver(): Promise<SynapseSqliteDriver> {
  if (isBun) {
    const { Database } = await import("bun:sqlite");
    return Database as unknown as SynapseSqliteDriver;
  }
  const { default: Database } = await import("better-sqlite3");
  return Database;
}
export function prefix(data: object) {
  return isBun
    ? Object.fromEntries(Object.entries(data).map(([key, value]) => [`$${key}`, value]))
    : data;
}

const bunRewrite = <T extends object>(data: T) =>
  Object.fromEntries(
    Object.entries(data)
      .filter(([, value]) => !is.undefined(value))
      .map(([key, value]) => [key, is.object(value) && "current" in value ? "dynamic" : value]),
  ) as T;

export async function SQLiteService({
  lifecycle,
  config,
  logger,
  hass,
  internal,
  synapse,
}: TServiceParams): Promise<SynapseSqlite> {
  let database: Database;

  const application_name = internal.boot.application.name;
  const Driver = await getDriver();
  const registeredDefaults = new Map<string, object>();

  lifecycle.onPostConfig(() => {
    logger.trace("create if not exists tables");
    database = new Driver(config.synapse.SQLITE_DB);
    database.prepare(ENTITY_CREATE).run();
    database.prepare(LOCALS_CREATE).run();
  });

  lifecycle.onShutdownStart(() => {
    logger.trace("close database");
    database.close();
  });

  // #MARK: update
  function update(unique_id: TSynapseId, content: object, defaults?: object) {
    const entity_id = hass.entity.registry?.current?.find(
      i => i.unique_id === unique_id,
    )?.entity_id;
    if (is.empty(entity_id)) {
      if (synapse.configure.isRegistered()) {
        logger.warn(
          { name: update, unique_id },
          `app registered, but entity does not exist (reload?)`,
        );
        return;
      }
      logger.warn("app not registered, skipping write");
      return;
    }
    const state_json = JSON.stringify(content);
    const now = new Date().toISOString();
    const insert = database.prepare(ENTITY_UPSERT);
    defaults ??= registeredDefaults.get(unique_id);
    const data = prefix({
      application_name: application_name,
      base_state: JSON.stringify(defaults),
      entity_id: entity_id,
      first_observed: now,
      last_modified: now,
      last_reported: now,
      state_json: state_json,
      unique_id: unique_id,
    });
    logger.trace({ ...data }, "update entity");
    insert.run(data);
  }

  // #MARK: loadRow
  function loadRow<LOCALS extends object = object>(unique_id: TSynapseId) {
    logger.trace({ unique_id }, "load entity");
    const row = database
      .prepare<[TSynapseId, string], HomeAssistantEntityRow<LOCALS>>(SELECT_QUERY)
      .get(unique_id, application_name);
    if (!row) {
      logger.debug("entity not found in database");
      return undefined;
    }
    logger.trace({ entity_id: row.entity_id, unique_id }, "load entity");
    return row;
  }

  /**
   * remove properties that were defaulted to undefined by internal workflows
   */
  function loadBaseState(base: string): object {
    const current = JSON.parse(base);
    return Object.fromEntries(
      Object.keys(current)
        .filter(key => !is.undefined(current[key]))
        .map(key => [key, current[key]]),
    );
  }

  // #MARK: load
  function load<LOCALS extends object = object>(
    unique_id: TSynapseId,
    defaults: object,
  ): HomeAssistantEntityRow<LOCALS> {
    // - if exists, return existing data
    const data = loadRow<LOCALS>(unique_id);
    const cleaned = bunRewrite(defaults);
    registeredDefaults.set(unique_id, cleaned);
    if (data) {
      const current = loadBaseState(data.base_state);
      if (is.equal(cleaned, current)) {
        logger.trace({ unique_id }, "equal defaults");
        return data;
      }
      logger.debug(
        { cleaned, current, unique_id },
        "hard config change detected, resetting entity",
      );
      // might do some smart merge logic later 🤷‍♀️
      // technically no specific action is needed here since the below will override
    }
    // - if new: insert then try again
    logger.trace({ name: load, unique_id }, `creating new sqlite entry`);
    update(unique_id, cleaned, cleaned);
    return loadRow<LOCALS>(unique_id);
  }

  return {
    getDatabase: () => database,
    load,
    update,
  };
}
