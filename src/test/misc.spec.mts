import {
  ApplicationDefinition,
  OptionalModuleConfiguration,
  ServiceMap,
} from "@digital-alchemy/core";

import { isReactiveConfig, md5ToUUID, NO_LIVE_UPDATE } from "../helpers/index.mts";

describe("Misc", () => {
  let application: ApplicationDefinition<ServiceMap, OptionalModuleConfiguration>;

  afterEach(async () => {
    if (application) {
      await application.teardown();
      application = undefined;
    }
    vi.restoreAllMocks();
  });

  // #MARK: isReactiveConfig
  describe("isReactiveConfig", () => {
    it("should return true for valid ReactiveConfig object and key", () => {
      const validKey = "valid_key";
      const validValue = { current: () => {} };

      expect(isReactiveConfig(validKey, validValue)).toBe(true);
    });

    it('should return false if key is "attributes"', () => {
      const key = "attributes";
      const value = { current: () => {} };

      expect(isReactiveConfig(key, value)).toBe(false);
    });

    it("should return false if key is in NO_LIVE_UPDATE set", () => {
      NO_LIVE_UPDATE.forEach(key => {
        const value = { current: () => {} };
        expect(isReactiveConfig(key, value)).toBe(false);
      });
    });

    it("should return false if value does not have a current function", () => {
      const validKey = "valid_key";
      const invalidValue = { current: "not a function" };

      expect(isReactiveConfig(validKey, invalidValue)).toBe(false);
    });

    it("should return false if value is not an object", () => {
      const validKey = "valid_key";
      const invalidValue = "not an object";

      expect(isReactiveConfig(validKey, invalidValue)).toBe(false);
    });
  });

  // #MARK: md5ToUUID
  describe("md5ToUUID", () => {
    it("should return the same string if it already contains hyphens", () => {
      const md5WithHyphens = "123e4567-e89b-12d3-a456-426614174000";
      expect(md5ToUUID(md5WithHyphens)).toBe(md5WithHyphens);
    });

    it("should format a valid md5 string without hyphens into a UUID format", () => {
      const md5 = "123e4567e89b12d3a456426614174000";
      const expectedUUID = "123e4567-e89b-12d3-a456-426614174000";

      expect(md5ToUUID(md5)).toBe(expectedUUID);
    });

    it("should handle short md5 strings by formatting only available characters", () => {
      const shortMd5 = "1234567890abcdef";
      const expectedUUID = "12345678-90ab-cdef--";

      expect(md5ToUUID(shortMd5)).toBe(expectedUUID);
    });

    it("should return an empty string if md5 is empty", () => {
      expect(md5ToUUID("")).toBe("----");
    });
  });
});
