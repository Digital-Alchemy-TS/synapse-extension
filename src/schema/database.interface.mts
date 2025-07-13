// Common database interface that all database services must implement
export type SynapseDatabase = {
  getDatabase: () => unknown;
  load: <LOCALS extends object = object>(
    unique_id: string,
    defaults: object,
  ) => Promise<HomeAssistantEntityRow<LOCALS>>;
  update: (unique_id: string, content: object, defaults?: object) => Promise<void>;
  updateLocal: (unique_id: string, key: string, content: unknown) => Promise<void>;
  loadLocals: (unique_id: string) => Promise<Map<string, unknown>>;
  deleteLocal: (unique_id: string, key: string) => Promise<void>;
  deleteLocalsByUniqueId: (unique_id: string) => Promise<void>;
};

// Common entity row type that normalizes different database types
export type HomeAssistantEntityRow<LOCALS extends object = object> = {
  unique_id: string;
  entity_id: string;
  app_unique_id: string;
  application_name: string;
  base_state: string;
  first_observed: string;
  id: number;
  last_modified: string;
  last_reported: string;
  state_json: string;
  locals: LOCALS;
};
