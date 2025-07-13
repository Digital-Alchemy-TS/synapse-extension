import { jsonb, pgTable, serial, text, timestamp } from "drizzle-orm/pg-core";

// HomeAssistantEntity table - Main entity storage
export const homeAssistantEntity = pgTable("HomeAssistantEntity", {
  app_unique_id: text("app_unique_id").notNull(),
  application_name: text("application_name").notNull(),
  base_state: text("base_state").notNull(),
  entity_id: text("entity_id").notNull(),
  first_observed: timestamp("first_observed").notNull().defaultNow(),
  id: serial("id").primaryKey(),
  last_modified: text("last_modified").notNull(),
  last_reported: text("last_reported").notNull(),
  state_json: jsonb("state_json").notNull(),
  unique_id: text("unique_id").notNull().unique(),
});

// HomeAssistantEntityLocals table - Local entity data
export const homeAssistantEntityLocals = pgTable("HomeAssistantEntityLocals", {
  app_unique_id: text("app_unique_id").notNull(),
  id: serial("id").primaryKey(),
  key: text("key").notNull(),
  last_modified: timestamp("last_modified").notNull().defaultNow(),
  unique_id: text("unique_id").notNull(),
  value_json: jsonb("value_json").notNull(),
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
