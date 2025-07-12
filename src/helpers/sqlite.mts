import { PICK_ENTITY } from "@digital-alchemy/hass";

export const ENTITY_CREATE = `CREATE TABLE IF NOT EXISTS HomeAssistantEntity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  unique_id TEXT NOT NULL UNIQUE,
  entity_id TEXT NOT NULL,
  state_json TEXT NOT NULL,
  base_state TEXT NOT NULL,
  first_observed DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_reported DATETIME NOT NULL,
  last_modified DATETIME NOT NULL,
  application_name TEXT NOT NULL
)`;

export const LOCALS_CREATE = `CREATE TABLE IF NOT EXISTS HomeAssistantEntityLocals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  unique_id INTEGER NOT NULL,
  key TEXT NOT NULL,
  value_json TEXT NOT NULL,
  last_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (unique_id, key)
)`;

export const ENTITY_UPSERT = `INSERT INTO HomeAssistantEntity (
  unique_id,
  entity_id,
  state_json,
  first_observed,
  last_reported,
  last_modified,
  base_state,
  application_name
) VALUES (
  $unique_id,
  $entity_id,
  $state_json,
  $first_observed,
  $last_reported,
  $last_modified,
  $base_state,
  $application_name
) ON CONFLICT(unique_id) DO UPDATE SET
  entity_id = excluded.entity_id,
  last_reported = excluded.last_reported,
  last_modified = excluded.last_modified,
  state_json = excluded.state_json,
  base_state = excluded.base_state,
  application_name = excluded.application_name`;

export const ENTITY_LOCALS_UPSERT = `INSERT INTO HomeAssistantEntityLocals (
  unique_id, key, value_json, last_modified
) VALUES (
  $unique_id, $key, $value_json, $last_modified
) ON CONFLICT(unique_id, key) DO UPDATE SET
  value_json = excluded.value_json,
  last_modified = excluded.last_modified`;

export const DELETE_LOCALS_BY_UNIQUE_ID_QUERY = `DELETE FROM HomeAssistantEntityLocals WHERE unique_id = ?`;
export const DELETE_LOCALS_QUERY = `DELETE FROM HomeAssistantEntityLocals WHERE unique_id = ? AND key = ?`;
export const SELECT_LOCALS_QUERY = `SELECT * FROM HomeAssistantEntityLocals WHERE unique_id = ?`;
export const SELECT_QUERY = `SELECT * FROM HomeAssistantEntity WHERE unique_id = ? AND application_name = ?`;

export type HomeAssistantEntityLocalRow = {
  id?: number;
  entity_id: string;
  key: string;
  value_json: string;
  last_modified: string;
};

export type HomeAssistantEntityRow<LOCALS extends object = object> = {
  id?: number;
  unique_id: string;
  entity_id: PICK_ENTITY;
  state_json: string;
  first_observed: string;
  last_reported: string;
  last_modified: string;
  base_state: string;
  application_name: string;
  locals: LOCALS;
};
