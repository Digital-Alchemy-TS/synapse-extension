import { CreateLibrary, createModule, StringConfig } from "@digital-alchemy/core";
import { LIB_HASS } from "@digital-alchemy/hass";
import { LIB_MOCK_ASSISTANT } from "@digital-alchemy/hass/mock-assistant";

import { LIB_SYNAPSE } from "../synapse.module.mts";
import { MockSynapseConfiguration } from "./extensions/configuration.service.mts";

enum CleanupOptions {
  before = "before",
  after = "after",
  none = "none",
}

enum InstallState {
  none = "none",
  registered = "registered",
  configured = "configured",
  ignore = "ignore",
}

export const LIB_MOCK_SYNAPSE = CreateLibrary({
  configuration: {
    CLEANUP_DB: {
      default: "after",
      enum: Object.values(CleanupOptions),
      type: "string",
    } as StringConfig<`${CleanupOptions}`>,
    INSTALL_STATE: {
      default: "configured",
      enum: Object.values(InstallState),
      type: "string",
    } as StringConfig<`${InstallState}`>,
  },
  depends: [LIB_HASS, LIB_SYNAPSE, LIB_MOCK_ASSISTANT],
  name: "mock_synapse",
  priorityInit: [],
  services: {
    config: MockSynapseConfiguration,
  },
});

declare module "@digital-alchemy/core" {
  export interface LoadedModules {
    mock_synapse: typeof LIB_MOCK_SYNAPSE;
  }
}

export const synapseTestRunner = createModule
  .fromLibrary(LIB_SYNAPSE)
  .extend()
  .toTest()
  .setOptions({ configSources: { argv: false, env: false, file: false } })
  .appendLibrary(LIB_MOCK_SYNAPSE)
  .appendLibrary(LIB_MOCK_ASSISTANT);
