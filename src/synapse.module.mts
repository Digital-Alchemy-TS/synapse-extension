import { CreateLibrary, InternalConfig, StringConfig } from "@digital-alchemy/core";
import { LIB_HASS } from "@digital-alchemy/hass";
import { join } from "path";
import { cwd } from "process";

import { HassDeviceMetadata } from "./helpers/index.mts";
import {
  ConfigurationService,
  DatabaseService,
  DeviceService,
  DiscoveryService,
  DomainGeneratorService,
  StorageService,
  SynapseLocalsService,
  SynapseSocketService,
  VirtualBinarySensor,
  VirtualButton,
  VirtualDate,
  VirtualDateTime,
  VirtualLock,
  VirtualNumber,
  VirtualScene,
  VirtualSelect,
  VirtualSensor,
  VirtualSwitch,
  VirtualText,
  VirtualTime,
} from "./services/index.mts";

const DOMAINS = {
  //   alarm_control_panel: VirtualAlarmControlPanel,
  binary_sensor: VirtualBinarySensor,
  button: VirtualButton,
  //   camera: VirtualCamera,
  //   climate: VirtualClimate,
  //   cover: VirtualCover,
  /**
   * ### Customize date type
   *
   * Provides `YYYY-MM-DD` format by default
   *
   * > Available options: `iso` | `date` | `dayjs`
   *
   * ```typescript
   * synapse.date<{ date_type: "dayjs" }>({ ... })
   * ```
   */
  date: VirtualDate,
  /**
   * ### Customize datetime type
   *
   * > Available options: `iso` | `date` | `dayjs`
   *
   * ```typescript
   * synapse.datetime<{ date_type: "dayjs" }>({ ... })
   * ```
   */
  datetime: VirtualDateTime,
  //   fan: VirtualFan,
  //   image: VirtualImage,
  //   lawn_mower: VirtualLawnMower,
  //   light: VirtualLight,
  lock: VirtualLock,
  //   media_player: VirtualMediaPlayer,
  //   notify: VirtualNotify,
  number: VirtualNumber,
  //   remote: VirtualRemote,
  scene: VirtualScene,
  select: VirtualSelect,
  /**
   * ### Customize state
   *
   * > Available options: `number` | `string`
   *
   * ```typescript
   * synapse.sensor<{ state: number }>({ ... })
   * ```
   */
  sensor: VirtualSensor,
  //   siren: VirtualSiren,
  switch: VirtualSwitch,
  text: VirtualText,
  time: VirtualTime,
  //   todo_list: VirtualTodoList,
  //   update: VirtualUpdate,
  //   vacuum: VirtualVacuum,
  //   valve: VirtualValve,
  //   water_heater: VirtualWaterHeater,
};

export const LIB_SYNAPSE = CreateLibrary({
  configuration: {
    DATABASE_TYPE: {
      default: "sqlite",
      description: "Database type to use (sqlite, postgresql, mysql)",
      enum: ["sqlite", "postgresql", "mysql"],
      type: "string",
    } as StringConfig<"sqlite" | "postgresql" | "mysql">,
    DATABASE_URL: {
      default: `file:${join(cwd(), "synapse_storage.db")}`,
      description: "Database connection URL",
      type: "string",
    },
    EMIT_HEARTBEAT: {
      default: true,
      description: [
        "Emit a heartbeat pulse so the extension knows the service is alive",
        "Disable for tests",
      ],
      type: "boolean",
    },
    EVENT_NAMESPACE: {
      default: "digital_alchemy",
      description: [
        "You almost definitely do not want to change this",
        "Must be matched on the python integration side (probably don't change this)",
      ],
      type: "string",
    },
    HEARTBEAT_INTERVAL: {
      default: 5,
      description: "Seconds between heartbeats",
      type: "number",
    },
    METADATA: {
      description: "Extra data to describe the app + build default device from",
      type: "internal",
    } as InternalConfig<HassDeviceMetadata>,
    METADATA_TITLE: {
      description: ["Title for the integration provided by this app", "Defaults to app name"],
      type: "string",
    },
    METADATA_UNIQUE_ID: {
      description: ["A string to uniquely identify this application", "Should be uuid or md5 sum"],
      type: "string",
    },
    TRACE_SIBLING_HEARTBEATS: {
      default: false,
      description: [
        "Set to true to output debug info about other synapse apps emitting heartbeats to the same instance of Home Assistant",
        "Logs emitted at trace level, for debugging only",
      ],
      type: "boolean",
    },
  },
  depends: [LIB_HASS],
  name: "synapse",
  priorityInit: ["locals", "generator", "storage"],
  services: {
    /**
     * @internal
     */
    configure: ConfigurationService,

    /**
     * Internal tools to create the device that registers with entities
     */
    device: DeviceService,

    /**
     * @internal
     *
     * Discovery features
     */
    discovery: DiscoveryService,

    /**
     * @internal
     *
     * Used to assist creation of domains
     */
    generator: DomainGeneratorService,

    /**
     * @internal
     *
     * Used to power `synapseEntity.locals`
     */
    locals: SynapseLocalsService,

    /**
     * @internal
     */
    socket: SynapseSocketService,

    /**
     * @internal
     *
     * Used to persist entity state
     */
    sqlite: DatabaseService,

    /**
     * @internal
     */
    storage: StorageService,
    ...DOMAINS,
  },
});

declare module "@digital-alchemy/core" {
  export interface LoadedModules {
    /**
     * tools for creating new entities within home assistant
     */
    synapse: typeof LIB_SYNAPSE;
  }
}
