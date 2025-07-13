import { is, TServiceParams } from "@digital-alchemy/core";
import Database from "better-sqlite3";
import { and, eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";

import { HomeAssistantEntityRow, SynapseDatabase } from "../schema/database.interface.mts";
import { homeAssistantEntity, homeAssistantEntityLocals } from "../schema/tables.mts";

export async function DatabaseSQLiteService({
  lifecycle,
  config,
  logger,
  hass,
  internal,
  synapse,
}: TServiceParams): Promise<SynapseDatabase> {
  let sqlite: Database.Database;
  let database: ReturnType<typeof drizzle>;

  const application_name = internal.boot.application.name;
  const app_unique_id = config.synapse.METADATA_UNIQUE_ID;
  const registeredDefaults = new Map<string, object>();

  lifecycle.onPostConfig(async () => {
    // Only connect if this is the configured database type
    if (config.synapse.DATABASE_TYPE !== "sqlite") {
      return;
    }

    logger.trace("initializing SQLite database connection");

    const filePath = config.synapse.DATABASE_URL.replace("file:", "");
    sqlite = new Database(filePath);
    database = drizzle(sqlite);

    // Run migrations
    try {
      await migrate(database, { migrationsFolder: "./src/schema/migrations/sqlite" });
      logger.trace("SQLite database migrations completed");
    } catch (error) {
      logger.warn("migration failed, continuing with existing schema", error);
    }
  });

  lifecycle.onShutdownStart(() => {
    if (config.synapse.DATABASE_TYPE === "sqlite" && sqlite) {
      logger.trace("closing SQLite database connection");
      sqlite.close();
    }
  });

  // Update entity
  async function update(unique_id: string, content: object, defaults?: object) {
    if (config.synapse.DATABASE_TYPE !== "sqlite" || !database) {
      return;
    }

    const entity_id = hass.entity.registry.current.find(i => i.unique_id === unique_id)?.entity_id;
    if (!entity_id) {
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
    defaults ??= registeredDefaults.get(unique_id);

    try {
      await database
        .insert(homeAssistantEntity)
        .values({
          app_unique_id: app_unique_id,
          application_name: application_name,
          base_state: JSON.stringify(defaults),
          entity_id: entity_id,
          first_observed: now,
          last_modified: now,
          last_reported: now,
          state_json: state_json,
          unique_id: unique_id,
        })
        .onConflictDoUpdate({
          set: {
            app_unique_id: app_unique_id,
            application_name: application_name,
            base_state: JSON.stringify(defaults),
            entity_id: entity_id,
            last_modified: now,
            last_reported: now,
            state_json: state_json,
          },
          target: homeAssistantEntity.unique_id,
        });

      logger.trace({ unique_id }, "updated entity");
    } catch (error) {
      logger.error({ error, unique_id }, "failed to update entity");
      throw error;
    }
  }

  // Load entity row
  async function loadRow<LOCALS extends object = object>(
    unique_id: string,
  ): Promise<HomeAssistantEntityRow<LOCALS>> {
    if (config.synapse.DATABASE_TYPE !== "sqlite" || !database) {
      throw new Error("SQLite database not configured or not connected");
    }

    logger.trace({ unique_id }, "loading entity");

    try {
      const rows = await database
        .select()
        .from(homeAssistantEntity)
        .where(
          and(
            eq(homeAssistantEntity.unique_id, unique_id),
            eq(homeAssistantEntity.app_unique_id, app_unique_id),
          ),
        );

      if (is.empty(rows)) {
        return undefined;
      }

      const [row] = rows;

      // Normalize data to match common interface
      const normalizedRow: HomeAssistantEntityRow<LOCALS> = {
        app_unique_id: row.app_unique_id,
        application_name: row.application_name,
        base_state:
          typeof row.base_state === "string" ? row.base_state : JSON.stringify(row.base_state),
        entity_id: row.entity_id,
        first_observed: row.first_observed,
        id: row.id,
        last_modified: row.last_modified,
        last_reported: row.last_reported,
        locals: {} as LOCALS,
        state_json:
          typeof row.state_json === "string" ? row.state_json : JSON.stringify(row.state_json),
        unique_id: row.unique_id,
      };

      logger.trace({ entity_id: row.entity_id, unique_id }, "loaded entity");
      return normalizedRow;
    } catch (error) {
      logger.error({ error, unique_id }, "failed to load entity");
      throw error;
    }
  }

  // Load entity with defaults
  async function load<LOCALS extends object = object>(
    unique_id: string,
    defaults: object,
  ): Promise<HomeAssistantEntityRow<LOCALS>> {
    if (config.synapse.DATABASE_TYPE !== "sqlite") {
      throw new Error("SQLite database not configured");
    }

    try {
      const data = await loadRow<LOCALS>(unique_id);
      const cleaned = Object.fromEntries(
        Object.entries(defaults).filter(([, value]) => value !== undefined),
      );
      registeredDefaults.set(unique_id, cleaned);

      const current = data ? JSON.parse(data.base_state) : {};
      if (data && JSON.stringify(cleaned) === JSON.stringify(current)) {
        logger.trace({ unique_id }, "equal defaults");
        return data;
      }
      logger.debug(
        { cleaned, current, unique_id },
        "hard config change detected, resetting entity",
      );
    } catch (error) {
      // Check if this is the expected "entity not found" error
      if (error instanceof Error && error.message.includes("Entity not found")) {
        logger.trace({ name: load, unique_id }, `creating new database entry`);
      } else {
        // Re-throw unexpected errors
        throw error;
      }
    }

    const cleaned = Object.fromEntries(
      Object.entries(defaults).filter(([, value]) => value !== undefined),
    );
    await update(unique_id, cleaned, cleaned);
    return await loadRow<LOCALS>(unique_id);
  }

  // Update local storage
  async function updateLocal(unique_id: string, key: string, content: unknown) {
    if (config.synapse.DATABASE_TYPE !== "sqlite" || !database) {
      return;
    }

    logger.trace({ key, unique_id }, "updateLocal");

    if (content === undefined) {
      await deleteLocal(unique_id, key);
      return;
    }

    const value_json = JSON.stringify(content);
    const last_modified = new Date().toISOString();

    try {
      await database
        .insert(homeAssistantEntityLocals)
        .values({
          app_unique_id: app_unique_id,
          key,
          last_modified: last_modified,
          unique_id: unique_id,
          value_json: value_json,
        })
        .onConflictDoUpdate({
          set: {
            app_unique_id: app_unique_id,
            last_modified: last_modified,
            value_json: value_json,
          },
          target: [homeAssistantEntityLocals.unique_id, homeAssistantEntityLocals.key],
        });

      logger.trace({ key, unique_id }, "updated local");
    } catch (error) {
      logger.error({ error, key, unique_id }, "failed to update local");
      throw error;
    }
  }

  // Load locals
  async function loadLocals(unique_id: string): Promise<Map<string, unknown>> {
    if (config.synapse.DATABASE_TYPE !== "sqlite" || !database) {
      throw new Error("SQLite database not configured or not connected");
    }

    if (!internal.boot.completedLifecycleEvents.has("PostConfig")) {
      throw new Error("Cannot load locals before [PostConfig]");
    }

    logger.trace({ unique_id }, "initial load of locals");

    try {
      const locals = await database
        .select()
        .from(homeAssistantEntityLocals)
        .where(
          and(
            eq(homeAssistantEntityLocals.unique_id, unique_id),
            eq(homeAssistantEntityLocals.app_unique_id, app_unique_id),
          ),
        );

      return new Map<string, unknown>(locals.map(i => [i.key, JSON.parse(i.value_json)]));
    } catch (error) {
      logger.error({ error, unique_id }, "failed to load locals");
      throw error;
    }
  }

  // Delete local
  async function deleteLocal(unique_id: string, key: string) {
    if (config.synapse.DATABASE_TYPE !== "sqlite" || !database) {
      return;
    }

    logger.debug({ key, unique_id }, `delete local (value undefined)`);

    try {
      await database
        .delete(homeAssistantEntityLocals)
        .where(
          and(
            eq(homeAssistantEntityLocals.unique_id, unique_id),
            eq(homeAssistantEntityLocals.key, key),
            eq(homeAssistantEntityLocals.app_unique_id, app_unique_id),
          ),
        );
    } catch (error) {
      logger.error({ error, key, unique_id }, "failed to delete local");
      throw error;
    }
  }

  // Delete all locals for unique_id
  async function deleteLocalsByUniqueId(unique_id: string) {
    if (config.synapse.DATABASE_TYPE !== "sqlite" || !database) {
      return;
    }

    logger.debug({ unique_id }, "delete all locals");

    try {
      await database
        .delete(homeAssistantEntityLocals)
        .where(
          and(
            eq(homeAssistantEntityLocals.unique_id, unique_id),
            eq(homeAssistantEntityLocals.app_unique_id, app_unique_id),
          ),
        );
    } catch (error) {
      logger.error({ error, unique_id }, "failed to delete locals");
      throw error;
    }
  }

  return {
    deleteLocal,
    deleteLocalsByUniqueId,
    getDatabase: () => database,
    load,
    loadLocals,
    update,
    updateLocal,
  };
}
