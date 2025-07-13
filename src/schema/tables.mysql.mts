import { int, mysqlTable, timestamp, varchar } from "drizzle-orm/mysql-core";

// HomeAssistantEntity table - Main entity storage
export const homeAssistantEntity = mysqlTable("HomeAssistantEntity", {
  app_unique_id: varchar("app_unique_id", { length: 255 }).notNull(),
  application_name: varchar("application_name", { length: 255 }).notNull(),
  base_state: varchar("base_state", { length: 1000 }).notNull(),
  entity_id: varchar("entity_id", { length: 255 }).notNull(),
  first_observed: timestamp("first_observed").notNull().defaultNow(),
  id: int("id").primaryKey().autoincrement(),
  last_modified: varchar("last_modified", { length: 255 }).notNull(),
  last_reported: varchar("last_reported", { length: 255 }).notNull(),
  state_json: varchar("state_json", { length: 1000 }).notNull(),
  unique_id: varchar("unique_id", { length: 255 }).notNull().unique(),
});

// HomeAssistantEntityLocals table - Local entity data
export const homeAssistantEntityLocals = mysqlTable("HomeAssistantEntityLocals", {
  app_unique_id: varchar("app_unique_id", { length: 255 }).notNull(),
  id: int("id").primaryKey().autoincrement(),
  key: varchar("key", { length: 255 }).notNull(),
  last_modified: timestamp("last_modified").notNull().defaultNow(),
  unique_id: varchar("unique_id", { length: 255 }).notNull(),
  value_json: varchar("value_json", { length: 1000 }).notNull(),
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
