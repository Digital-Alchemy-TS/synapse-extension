import { CreateApplication } from "@digital-alchemy/core";
import { LIB_HASS } from "@digital-alchemy/hass";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import isBetween from "dayjs/plugin/isBetween";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";
import weekOfYear from "dayjs/plugin/weekOfYear";

import { LIB_SYNAPSE } from "../synapse.module.mts";
import { DemoEntityGenerator } from "./generator.mts";

dayjs.extend(weekOfYear);
dayjs.extend(advancedFormat);
dayjs.extend(isBetween);
dayjs.extend(utc);
dayjs.extend(timezone);

export const DEMO_APP = CreateApplication({
  libraries: [LIB_HASS, LIB_SYNAPSE],
  name: "synapse_demo",
  services: {
    generator: DemoEntityGenerator,
  },
});

declare module "@digital-alchemy/core" {
  export interface LoadedModules {
    synapse_demo: typeof DEMO_APP;
  }
}

await DEMO_APP.bootstrap({
  configuration: {
    boilerplate: { LOG_LEVEL: "debug" },
    synapse: {
      METADATA: {
        hw_version: "1.0.0",
        manufacturer: "Digital Alchemy",
        model: "Synapse Demo Device",
        suggested_area: "Demo Room",
      },
      METADATA_TITLE: "Synapse Demo Integration",
      METADATA_UNIQUE_ID: "synapse-demo-integration",
    },
  },
});
