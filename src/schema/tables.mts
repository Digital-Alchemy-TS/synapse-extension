import { sql } from "drizzle-orm";
import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

// HomeAssistantEntity table - Main entity storage
export const homeAssistantEntity = sqliteTable("HomeAssistantEntity", {
  app_unique_id: text("app_unique_id").notNull(),
  application_name: text("application_name").notNull(),
  base_state: text("base_state").notNull(),
  entity_id: text("entity_id").notNull(),
  first_observed: text("first_observed")
    .notNull()
    .default(sql`CURRENT_TIMESTAMP`),
  id: integer("id").primaryKey({ autoIncrement: true }),
  last_modified: text("last_modified").notNull(),
  last_reported: text("last_reported").notNull(),
  state_json: text("state_json").notNull(),
  unique_id: text("unique_id").notNull().unique(),
});

// HomeAssistantEntityLocals table - Local entity data
export const homeAssistantEntityLocals = sqliteTable("HomeAssistantEntityLocals", {
  app_unique_id: text("app_unique_id").notNull(),
  id: integer("id").primaryKey({ autoIncrement: true }),
  key: text("key").notNull(),
  last_modified: text("last_modified")
    .notNull()
    .default(sql`CURRENT_TIMESTAMP`),
  unique_id: text("unique_id").notNull(),
  value_json: text("value_json").notNull(),
});

// Type exports for use in the application
export type HomeAssistantEntity = typeof homeAssistantEntity.$inferSelect;
export type NewHomeAssistantEntity = typeof homeAssistantEntity.$inferInsert;

export type HomeAssistantEntityLocal = typeof homeAssistantEntityLocals.$inferSelect;
export type NewHomeAssistantEntityLocal = typeof homeAssistantEntityLocals.$inferInsert;

// Extended types for the application
export type HomeAssistantEntityRow<LOCALS extends object = object> = HomeAssistantEntity & {
  locals: LOCALS;
};

// Database service interface
export type SynapseDatabase = {
  getDatabase: () => unknown;
  load: <LOCALS extends object = object>(
    unique_id: string,
    defaults: object,
  ) => Promise<HomeAssistantEntityRow<LOCALS> | undefined>;
  update: (unique_id: string, content: object, defaults?: object) => Promise<void>;
  updateLocal: (unique_id: string, key: string, content: unknown) => Promise<void>;
  loadLocals: (unique_id: string) => Promise<Map<string, unknown> | undefined>;
  deleteLocal: (unique_id: string, key: string) => Promise<void>;
  deleteLocalsByUniqueId: (unique_id: string) => Promise<void>;
};
