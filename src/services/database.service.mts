import { TServiceParams } from "@digital-alchemy/core";

import { SynapseDatabase } from "../schema/database.interface.mts";
import { DatabaseMySQLService } from "./database-mysql.service.mts";
import { DatabasePostgreSQLService } from "./database-pg.service.mts";
import { DatabaseSQLiteService } from "./database-sqlite.service.mts";

export async function DatabaseService(params: TServiceParams): Promise<SynapseDatabase> {
  const { config } = params;
  const sqliteService = await DatabaseSQLiteService(params);
  const postgresService = await DatabasePostgreSQLService(params);
  const mysqlService = await DatabaseMySQLService(params);

  return {
    deleteLocal: async (unique_id: string, key: string) => {
      switch (config.synapse.DATABASE_TYPE) {
        case "sqlite":
          await sqliteService.deleteLocal(unique_id, key);
          break;
        case "postgresql":
          await postgresService.deleteLocal(unique_id, key);
          break;
        case "mysql":
          await mysqlService.deleteLocal(unique_id, key);
          break;
      }
    },
    deleteLocalsByUniqueId: async (unique_id: string) => {
      switch (config.synapse.DATABASE_TYPE) {
        case "sqlite":
          await sqliteService.deleteLocalsByUniqueId(unique_id);
          break;
        case "postgresql":
          await postgresService.deleteLocalsByUniqueId(unique_id);
          break;
        case "mysql":
          await mysqlService.deleteLocalsByUniqueId(unique_id);
          break;
      }
    },
    getDatabase: () => {
      switch (config.synapse.DATABASE_TYPE) {
        case "sqlite":
          return sqliteService.getDatabase();
        case "postgresql":
          return postgresService.getDatabase();
        case "mysql":
          return mysqlService.getDatabase();
        default:
          return sqliteService.getDatabase();
      }
    },
    load: async <LOCALS extends object = object>(unique_id: string, defaults: object) => {
      switch (config.synapse.DATABASE_TYPE) {
        case "sqlite":
          return await sqliteService.load<LOCALS>(unique_id, defaults);
        case "postgresql":
          return await postgresService.load<LOCALS>(unique_id, defaults);
        case "mysql":
          return await mysqlService.load<LOCALS>(unique_id, defaults);
        default:
          return await sqliteService.load<LOCALS>(unique_id, defaults);
      }
    },
    loadLocals: async (unique_id: string) => {
      switch (config.synapse.DATABASE_TYPE) {
        case "sqlite":
          return await sqliteService.loadLocals(unique_id);
        case "postgresql":
          return await postgresService.loadLocals(unique_id);
        case "mysql":
          return await mysqlService.loadLocals(unique_id);
        default:
          return await sqliteService.loadLocals(unique_id);
      }
    },
    update: async (unique_id: string, content: object, defaults?: object) => {
      switch (config.synapse.DATABASE_TYPE) {
        case "sqlite":
          await sqliteService.update(unique_id, content, defaults);
          break;
        case "postgresql":
          await postgresService.update(unique_id, content, defaults);
          break;
        case "mysql":
          await mysqlService.update(unique_id, content, defaults);
          break;
      }
    },
    updateLocal: async (unique_id: string, key: string, content: unknown) => {
      switch (config.synapse.DATABASE_TYPE) {
        case "sqlite":
          await sqliteService.updateLocal(unique_id, key, content);
          break;
        case "postgresql":
          await postgresService.updateLocal(unique_id, key, content);
          break;
        case "mysql":
          await mysqlService.updateLocal(unique_id, key, content);
          break;
      }
    },
  };
}
