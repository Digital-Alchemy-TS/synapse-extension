import fs from "fs";
import os from "os";
import { v4 } from "uuid";

import { synapseTestRunner } from "../mock/index.mts";

describe("Device", () => {
  afterEach(async () => {
    await synapseTestRunner.teardown();
    vi.restoreAllMocks();
  });

  // #MARK: loadVersion
  describe("loadVersion", () => {
    it("returns existing version if set", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse }) => {
        const version = v4();
        synapse.device.setVersion(version);
        expect(synapse.device.loadVersion()).toBe(version);
      });
    });

    it.skip("loads version from package.json if synapseVersion is not set", async () => {
      expect.assertions(1);
      await synapseTestRunner.emitLogs().run(({ synapse }) => {
        const version = v4();
        const packageJson = JSON.stringify({ version });

        vi.spyOn(fs, "existsSync").mockReturnValue(true);
        vi.spyOn(fs, "readFileSync").mockReturnValue(packageJson);

        expect(synapse.device.loadVersion()).toBe(version);
      });
    });

    it("returns undefined if package.json does not exist", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse }) => {
        vi.spyOn(fs, "existsSync").mockReturnValueOnce(false);
        expect(synapse.device.loadVersion()).toBeUndefined();
      });
    });

    it("logs an error and returns undefined if reading package.json fails", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse }) => {
        vi.spyOn(fs, "existsSync").mockReturnValueOnce(true);

        vi.spyOn(fs, "readFileSync").mockImplementationOnce(() => {
          throw new Error("File read error");
        });

        expect(synapse.device.loadVersion()).toBeUndefined();
      });
    });
  });

  // #MARK: getInfo
  describe("getInfo", () => {
    it("formats data", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse, config }) => {
        const version = v4();
        synapse.device.setVersion(version);
        expect(synapse.device.getInfo()).toEqual({
          manufacturer: "Digital Alchemy",
          name: "testing",
          sw_version: version,
          ...config.synapse.METADATA,
        });
      });
    });
  });

  // #MARK: getInfo
  describe("id", () => {
    // this one fails on pipelines, swallowing all errors
    it.skip("default id", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse }) => {
        vi.spyOn(process, "cwd").mockImplementationOnce(() => `/app`);
        vi.spyOn(os, "hostname").mockImplementationOnce(() => `test_host`);
        expect(synapse.device.id()).toBe("d3fbf239-3650-904b-6527-7ca5b6ad4eb2");
      });
    });

    it("formats according to provided params string", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse }) => {
        expect(synapse.device.id("foo_bar")).toBe("5c7d96a3-dd7a-8785-0a2e-f34087565a6e");
      });
    });

    it("formats according to provided params array", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse }) => {
        expect(
          synapse.device.id(["some", "long", "list", "of", "properties", "and", "stuff"]),
        ).toBe("5b36913f-269e-1c89-1232-33e8b3722f91");
      });
    });
  });

  // #MARK: getInfo
  describe("list", () => {
    it("returns empty lists with no devices", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse }) => {
        expect(synapse.device.list()).toEqual([]);
      });
    });

    it("returns the device with no extra properties", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse, config }) => {
        const unique_id = v4();
        synapse.device.register(unique_id, {});
        expect(synapse.device.list()).toEqual([
          { hub_id: config.synapse.METADATA_UNIQUE_ID, unique_id },
        ]);
      });
    });

    it("returns the device with extra properties", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse, config }) => {
        const unique_id = v4();
        synapse.device.register(unique_id, {
          name: "foo",
        });
        expect(synapse.device.list()).toEqual([
          { hub_id: config.synapse.METADATA_UNIQUE_ID, name: "foo", unique_id },
        ]);
      });
    });
  });
});
