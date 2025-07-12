import { ANY_ENTITY } from "@digital-alchemy/hass";
import { v4 } from "uuid";

import { synapseTestRunner } from "../mock/index.mts";

describe("Generator", () => {
  afterEach(async () => {
    await synapseTestRunner.teardown();
    vi.restoreAllMocks();
  });

  // #MARK: isRegistered
  describe("operators", () => {
    const SENSOR_KEYS = [
      "getEntity",
      "storage",
      "onUpdate",
      "device_class",
      "last_reset",
      "state",
      "suggested_display_precision",
      "suggested_unit_of_measurement",
      "unit_of_measurement",
      "attributes",
      "device_id",
      "entity_category",
      "icon",
      "disabled",
      "name",
      "suggested_object_id",
      "translation_key",
      "unique_id",
    ];

    describe("delete", () => {
      it("does not allow deletes on non-locals", async () => {
        expect.assertions(SENSOR_KEYS.length);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor({ context, name: "test" });

          SENSOR_KEYS.forEach(i => expect(() => delete sensor[i as keyof typeof sensor]).toThrow());
        });
      });
    });

    describe("ownKeys", () => {
      it("returns correct keys", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor({ context, name: "test" });
          expect(Object.keys(sensor)).toEqual(expect.arrayContaining(["locals", ...SENSOR_KEYS]));
        });
      });
    });

    describe("has", () => {
      it("returns true for expected entities", async () => {
        expect.assertions(SENSOR_KEYS.length);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor({ context, name: "test" });
          SENSOR_KEYS.forEach(key => expect(key in sensor).toBe(true));
        });
      });

      it("returns true for unexpected entities", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor({ context, name: "test" });
          expect("unknown_key" in sensor).toBe(false);
        });
      });
    });

    describe("get", () => {
      const unique_id = v4();

      describe("getEntity", () => {
        it("getEntity stores and returns reference when entityRefs is empty", async () => {
          expect.assertions(2);
          vi.spyOn(console, "trace").mockImplementationOnce(() => undefined);
          await synapseTestRunner.run(({ synapse, context, hass }) => {
            const sensor = synapse.sensor({ context, name: "test", unique_id });
            const mockId = "new-id" as unknown as ANY_ENTITY;
            const mockRef = { entity_id: mockId };

            // @ts-expect-error wip test
            vi.spyOn(hass.idBy, "unique_id").mockReturnValueOnce(mockId);
            // @ts-expect-error wip test
            vi.spyOn(hass.refBy, "id").mockReturnValueOnce(mockRef);

            const result = sensor.getEntity();
            expect(hass.idBy.unique_id).toHaveBeenCalledWith(unique_id);
            expect(result).toBe(mockRef); // Should return the newly created reference
            // expect(entityRefs.get(mockId)).toBe(mockRef); // Ensure it’s stored in entityRefs
          });
        });

        it("getEntity attempts to look up by unique_id", async () => {
          expect.assertions(2);
          vi.spyOn(console, "trace").mockImplementationOnce(() => undefined);
          await synapseTestRunner.run(({ synapse, context, hass }) => {
            const sensor = synapse.sensor({ context, name: "test", unique_id });
            const spy = vi.spyOn(hass.idBy, "unique_id");
            sensor.getEntity();
            expect(spy).toHaveBeenCalledWith(unique_id);
            expect(spy).toHaveReturnedWith(undefined);
          });
        });
      });

      it("unknown properties return undefined", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor({ context, name: "test", unique_id });
          const INVALID_KEY = "some random key" as keyof typeof sensor;
          expect(sensor[INVALID_KEY]).toBeUndefined();
        });
      });

      describe("onUpdate", () => {
        it("watches for unique_id", async () => {
          expect.assertions(1);
          vi.spyOn(console, "trace").mockImplementationOnce(() => undefined);
          await synapseTestRunner.run(({ synapse, context, event }) => {
            const sensor = synapse.sensor({ context, name: "test", unique_id });
            const spy = vi.spyOn(event, "on");
            sensor.onUpdate(() => {});
            expect(spy).toHaveBeenCalledWith(unique_id, expect.any(Function));
          });
        });

        it("is removable", async () => {
          expect.assertions(1);
          vi.spyOn(console, "trace").mockImplementationOnce(() => undefined);
          await synapseTestRunner.run(({ synapse, context, event }) => {
            const sensor = synapse.sensor({ context, name: "test", unique_id });
            let removable: unknown;
            const spy = vi
              .spyOn(event, "on")
              // @ts-expect-error shut up
              .mockImplementation((_, callback) => (removable = callback));
            const { remove } = sensor.onUpdate(() => {});
            remove();
            expect(spy).toHaveBeenCalledWith(unique_id, removable);
          });
        });

        it("passes in correct params to callbacks", async () => {
          expect.assertions(1);
          vi.spyOn(console, "trace").mockImplementationOnce(() => undefined);
          await synapseTestRunner.run(({ synapse, context, event }) => {
            const sensor = synapse.sensor({ context, name: "test", unique_id });
            const callback = vi.fn();
            const { remove } = sensor.onUpdate(callback);
            const new_state = {};
            const old_state = {};
            event.emit(unique_id, new_state, old_state);
            expect(callback).toHaveBeenCalledWith(new_state, old_state, remove);
          });
        });

        it("wraps executions in safeExec", async () => {
          expect.assertions(1);
          vi.spyOn(console, "trace").mockImplementationOnce(() => undefined);
          await synapseTestRunner.run(({ synapse, context, event, internal }) => {
            const sensor = synapse.sensor({ context, name: "test", unique_id });
            const spy = vi.spyOn(internal, "safeExec");
            const callback = vi.fn();
            sensor.onUpdate(callback);
            event.emit(unique_id, {}, {});
            expect(spy).toHaveBeenCalled();
          });
        });
      });
    });

    describe("set", () => {
      it("does not allow setting of expected properties", async () => {
        expect.assertions(2);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor({ context, name: "test" });
          expect(() => {
            // @ts-expect-error it's the test
            sensor.unique_id = v4();
          }).toThrow();
          expect(() => {
            // @ts-expect-error it's the test
            sensor.some_random_property = v4();
          }).toThrow();
        });
      });
    });
  });

  describe("property interactions", () => {
    it("hard default is undefined", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
        lifecycle.onReady(() => {
          const sensor = synapse.sensor({ context, name: "test" });
          expect(sensor.icon).toBe(undefined);
        });
      });
    });

    it("default will use params", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
        lifecycle.onReady(() => {
          const sensor = synapse.sensor({ context, icon: "foo:bar", name: "test" });
          expect(sensor.icon).toBe("foo:bar");
        });
      });
    });

    it("tracks runtime values", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
        lifecycle.onReady(() => {
          const random = v4();
          const sensor = synapse.sensor({ context, icon: "foo:bar", name: "test" });
          sensor.icon = random;
          expect(sensor.icon).toBe(random);
        });
      });
    });
  });
});
