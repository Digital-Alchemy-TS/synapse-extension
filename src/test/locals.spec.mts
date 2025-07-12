import { v4 } from "uuid";

import { HomeAssistantEntityLocalRow } from "../helpers/index.mts";
import { synapseTestRunner } from "../mock/index.mts";

type SensorParams = {
  locals: {
    string?: string;
    test: boolean;
  };
};

describe("Locals", () => {
  afterEach(async () => {
    await synapseTestRunner.teardown();
    vi.restoreAllMocks();
  });

  it("exists", async () => {
    expect.assertions(1);
    await synapseTestRunner.run(({ synapse, context }) => {
      const sensor = synapse.sensor<SensorParams>({
        context,
        locals: { test: false },
        name: "test",
      });
      expect(sensor.locals).toBeDefined();
    });
  });

  // #MARK: Lifecycle
  describe("Lifecycle interactions", () => {
    it("sources defaults from definitions before sqlite is available", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse, context }) => {
        const sensor = synapse.sensor<SensorParams>({
          context,
          locals: { test: false },
          name: "test",
        });
        expect(sensor.locals.test).toBe(false);
      });
    });
  });

  // #MARK: Sqlite
  describe("sqlite interactions", () => {
    const unique_id = v4();

    it("loads sqlite data on first interaction only", async () => {
      expect.assertions(3);
      await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
        lifecycle.onReady(() => {
          const sensor = synapse.sensor<SensorParams>({
            context,
            locals: { test: false },
            name: "test",
          });
          const spy = vi.spyOn(synapse.sqlite, "getDatabase");
          expect(sensor.locals.test).toBe(false);
          expect(sensor.locals.test).toBe(false);
          expect(spy).toHaveBeenCalledTimes(1);
        });
      });
    });

    it("writes to sqlite on change", async () => {
      expect.assertions(1);
      await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
        lifecycle.onReady(() => {
          const sensor = synapse.sensor<SensorParams>({
            context,
            locals: { test: false },
            name: "test",
            unique_id,
          });
          const spy = vi.spyOn(synapse.locals, "updateLocal");
          sensor.locals.test = true;
          expect(spy).toHaveBeenCalledWith(unique_id, "test", true);
        });
      });
    });

    // #MARK: X-Run
    describe("Cross run", () => {
      it("returns set values", async () => {
        expect.assertions(2);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
              unique_id,
            });
            sensor.locals.test = true;
            expect(sensor.locals.test).toBe(true);

            const database = synapse.sqlite.getDatabase();
            const [entry] = database
              .prepare<
                [string],
                HomeAssistantEntityLocalRow
              >(`SELECT * FROM HomeAssistantEntityLocals WHERE unique_id = ?`)
              .all(unique_id);

            expect(entry).toEqual(
              expect.objectContaining({
                key: "test",
                unique_id,
                value_json: "true",
              }),
            );
          });
        });
      });

      it.skip("stored values take priority", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(
          ({ synapse, context, lifecycle }) => {
            lifecycle.onReady(() => {
              const sensor = synapse.sensor<SensorParams>({
                context,
                locals: { test: false },
                name: "test",
                unique_id,
              });
              expect(sensor.locals.test).toBe(true);
            });
          },
          // TODO: FIXME
          // { keepDb: true },
        );
      });
    });
  });

  describe("Operators", () => {
    // #MARK: deleteProperty
    describe("deleteProperty", () => {
      it("resets locals and deletes sqlite entries", async () => {
        expect.assertions(2);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const unique_id = v4();
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: true },
              name: "test",
              unique_id,
            });

            delete sensor.locals;

            const spy = vi.spyOn(synapse.sqlite, "getDatabase");

            const database = synapse.sqlite.getDatabase();
            const entry = database
              .prepare(`SELECT * FROM HomeAssistantEntityLocals WHERE unique_id = ?`)
              .all(unique_id);

            expect(spy).toHaveBeenCalled();
            expect(entry.length).toBe(0);
          });
        });
      });

      it("does not allow deletes before load", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor<SensorParams>({
            context,
            locals: { test: false },
            name: "test",
          });
          expect(() => {
            delete sensor.locals.test;
          }).toThrow();
        });
      });

      it("allows deletes for things that don't exist", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            expect(() => {
              // @ts-expect-error it's the test
              delete sensor.locals.this_does_not_exist;
            }).not.toThrow();
          });
        });
      });

      it("will return default value after deletion", async () => {
        expect.assertions(2);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            sensor.locals.test = true;
            expect(sensor.locals.test).toBe(true);
            delete sensor.locals.test;
            expect(sensor.locals.test).toBe(false);
          });
        });
      });
    });

    // #MARK: has
    describe("has", () => {
      it("has returns true for defaults", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            expect("test" in sensor.locals).toBe(true);
          });
        });
      });

      it("has returns true for defaults before ready", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor<SensorParams>({
            context,
            locals: { test: false },
            name: "test",
          });
          expect("test" in sensor.locals).toBe(true);
        });
      });

      it("has returns true for fields with values and defaults", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            sensor.locals.test = true;
            expect("test" in sensor.locals).toBe(true);
          });
        });
      });

      it("has returns false for fields with values no defaults and no values", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            expect("string" in sensor.locals).toBe(false);
          });
        });
      });

      it("has returns true for fields with values values but no defaults", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            sensor.locals.string = "foo";
            expect("string" in sensor.locals).toBe(true);
          });
        });
      });
    });

    // #MARK: ownKeys
    describe("ownKeys", () => {
      it("returns defaults as ownKeys before bootstrap", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const sensor = synapse.sensor<SensorParams>({
            context,
            locals: { test: false },
            name: "test",
          });
          expect(Object.keys(sensor.locals)).toEqual(["test"]);
        });
      });

      it("returns all keys from ownKeys as available", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, lifecycle }) => {
          lifecycle.onReady(() => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            sensor.locals.string = "foo";
            expect(Object.keys(sensor.locals)).toEqual(["test", "string"]);
          });
        });
      });
    });

    // #MARK: set
    describe.skip("set", () => {
      it("supports object assigns", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(
          ({ synapse, context, lifecycle }) => {
            lifecycle.onReady(() => {
              const sensor = synapse.sensor<SensorParams>({
                context,
                locals: { test: false },
                name: "test",
              });
              sensor.locals = { test: true };
              expect(sensor.locals.test).toBe(true);
            });
          },
          // { keepDb: true },
        );
      });

      it("does not support assign before db avail", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(
          ({ synapse, context }) => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            expect(() => {
              sensor.locals = { test: true };
            }).toThrow();
          },
          // { keepDb: true },
        );
      });

      it("should not allow sets before database is available", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(
          ({ synapse, context }) => {
            const sensor = synapse.sensor<SensorParams>({
              context,
              locals: { test: false },
              name: "test",
            });
            expect(() => {
              sensor.locals.test = false;
            }).toThrow();
          },
          // { keepDb: true },
        );
      });

      it("doesn't do anything if value didn't change", async () => {
        expect.assertions(2);
        await synapseTestRunner.run(
          ({ synapse, context, lifecycle }) => {
            lifecycle.onReady(() => {
              const sensor = synapse.sensor<SensorParams>({
                context,
                locals: { test: false },
                name: "test",
              });
              const spy = vi.spyOn(synapse.locals, "updateLocal");
              sensor.locals.test = false;
              expect(spy).toHaveBeenCalledTimes(1);
              sensor.locals.test = false;
              expect(spy).toHaveBeenCalledTimes(1);
            });
          },
          // { keepDb: true },
        );
      });
    });
  });
});
