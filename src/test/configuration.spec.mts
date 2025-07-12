import { TServiceParams } from "@digital-alchemy/core";
import { DeviceDetails, HassConfig, MIN_SUPPORTED_HASS_VERSION } from "@digital-alchemy/hass";
import { v4 } from "uuid";

import { synapseTestRunner } from "../mock/index.mts";

const NOT_INSTALLED = {
  components: [],
  version: MIN_SUPPORTED_HASS_VERSION,
} as HassConfig;
const INSTALLED = {
  components: ["synapse"],
  version: MIN_SUPPORTED_HASS_VERSION,
} as HassConfig;

describe("Configuration", () => {
  afterEach(async () => {
    await synapseTestRunner.teardown();
    vi.restoreAllMocks();
  });

  // #MARK: isRegistered
  describe("isRegistered", () => {
    it("returns false before checks", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse }: TServiceParams) => {
        expect(synapse.configure.isRegistered()).toBe(false);
      });
    });

    it("fails for not installed", async () => {
      expect.assertions(1);
      await synapseTestRunner
        .configure({ mock_synapse: { INSTALL_STATE: "ignore" } })
        .run(({ synapse, lifecycle, hass }: TServiceParams) => {
          vi.spyOn(hass.fetch, "getConfig").mockImplementation(async () => NOT_INSTALLED);
          lifecycle.onReady(() => {
            expect(synapse.configure.isRegistered()).toBe(false);
          });
        });
    });

    it("fails for installed but no device", async () => {
      expect.assertions(1);
      await synapseTestRunner
        .configure({ mock_synapse: { INSTALL_STATE: "ignore" } })
        .run(({ synapse, hass, lifecycle }: TServiceParams) => {
          vi.spyOn(hass.fetch, "getConfig").mockImplementation(async () => INSTALLED);
          lifecycle.onReady(() => {
            hass.device.current = [];
            expect(synapse.configure.isRegistered()).toBe(false);
          });
        });
    });

    it("passes for installed and with device", async () => {
      expect.assertions(1);
      const METADATA_UNIQUE_ID = v4();
      await synapseTestRunner
        .configure({
          mock_synapse: { INSTALL_STATE: "ignore" },
          synapse: { METADATA_UNIQUE_ID },
        })
        .run(({ synapse, hass, lifecycle }: TServiceParams) => {
          vi.spyOn(hass.fetch, "getConfig").mockImplementation(async () => INSTALLED);
          lifecycle.onReady(() => {
            hass.device.current = [
              { identifiers: [[undefined, METADATA_UNIQUE_ID]] } as DeviceDetails,
            ];
            expect(synapse.configure.isRegistered()).toBe(true);
          });
        });
    });
  });

  // #MARK: checkInstallState
  describe("checkInstallState", () => {
    it("passes when ASSUME_INSTALLED is true by default", async () => {
      expect.assertions(1);
      await synapseTestRunner
        // .configure({ synapse: { ASSUME_INSTALLED: true } })
        .run(({ synapse, lifecycle }: TServiceParams) => {
          lifecycle.onReady(async () => {
            expect(await synapse.configure.checkInstallState()).toBe(true);
          });
        });
    });

    it("fails when ASSUME_INSTALLED is false and integration does not exist", async () => {
      expect.assertions(1);
      await synapseTestRunner
        // .configure({ synapse: { ASSUME_INSTALLED: false } })
        .run(({ synapse, hass, lifecycle }: TServiceParams) => {
          vi.spyOn(hass.fetch, "getConfig").mockImplementation(async () => NOT_INSTALLED);
          lifecycle.onReady(async () => {
            vi.useFakeTimers();
            expect(await synapse.configure.checkInstallState()).toBe(false);
            vi.useRealTimers();
          });
        });
    });

    it("passes when ASSUME_INSTALLED is false and integration does exist", async () => {
      expect.assertions(1);
      await synapseTestRunner
        // .configure({ synapse: { ASSUME_INSTALLED: false } })
        .run(({ synapse, hass, lifecycle }: TServiceParams) => {
          vi.spyOn(hass.fetch, "getConfig").mockImplementation(async () => INSTALLED);
          lifecycle.onReady(async () => {
            vi.useFakeTimers();
            expect(await synapse.configure.checkInstallState()).toBe(true);
            vi.useRealTimers();
          });
        });
    });
  });
});
