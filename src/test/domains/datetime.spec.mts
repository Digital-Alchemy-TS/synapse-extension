import dayjs from "dayjs";
import { v4 } from "uuid";

import { synapseTestRunner } from "../../mock/index.mts";

const TESTING_DATE = `2024-01-01T00:00:00.000Z`;

describe("DateTime", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads the correct keys from storage", async () => {
    expect.assertions(1);
    await synapseTestRunner.run(({ synapse, context }) => {
      const spy = vi.spyOn(synapse.storage, "add");
      synapse.datetime({ context, name: "test" });
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          load_config_keys: ["native_value"],
        }),
      );
    });
  });

  describe("serialization", () => {
    describe("date", () => {
      it("events with correct types", async () => {
        const unique_id = v4();
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, config, hass, internal }) => {
          const entity = synapse.datetime<{ date_type: "date" }>({
            context,
            date_type: "date",
            name: "test",
            unique_id,
          });
          entity.onSetValue(({ value }) => {
            expect(value).toBeInstanceOf(Date);
          });
          hass.socket.socketEvents.emit(
            [config.synapse.EVENT_NAMESPACE, "set_value", internal.boot.application.name].join("/"),
            { data: { unique_id } },
          );
        });
      });

      it("loads from blank", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime({
            context,
            date_type: "date",
            name: "test",
          });
          expect(entity.native_value).toBeInstanceOf(Date);
        });
      });

      it("loads from defaulted", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime({
            context,
            date_type: "date",
            name: "test",
            native_value: new Date(TESTING_DATE),
          });
          expect(entity.native_value).toEqual(new Date(TESTING_DATE));
        });
      });

      it("can assign and retrieve", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "date" }>({
            context,
            date_type: "date",
            name: "test",
            native_value: new Date(TESTING_DATE),
          });
          const now = Date.now();
          entity.native_value = new Date(now);
          expect(entity.native_value).toEqual(new Date(now));
        });
      });

      it("will allow some unexpected types", async () => {
        expect.assertions(4);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "date" }>({
            context,
            date_type: "date",
            name: "test",
            native_value: new Date(TESTING_DATE),
          });
          const now = Date.now();
          // @ts-expect-error it's the test
          entity.native_value = dayjs(now);
          expect(entity.native_value).toEqual(new Date(now));
          // @ts-expect-error it's the test
          entity.native_value = now;
          expect(entity.native_value).toEqual(new Date(now));
          // @ts-expect-error it's the test
          entity.native_value = new Date(now).toISOString();
          expect(entity.native_value).toEqual(new Date(now));
          entity.native_value = undefined;
          expect(entity.native_value).toBeInstanceOf(Date);
        });
      });

      it("throws for invalid types", async () => {
        expect.assertions(4);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "date" }>({
            context,
            date_type: "date",
            name: "test",
            native_value: new Date(TESTING_DATE),
          });
          expect(() => {
            entity.native_value = null;
          }).toThrow();
          expect(() => {
            // @ts-expect-error it's the test
            entity.native_value = {};
          }).toThrow();
          expect(() => {
            // @ts-expect-error it's the test
            entity.native_value = Number.NaN;
          }).toThrow();
          expect(() => {
            entity.native_value = new Date("invalid date string");
          }).toThrow();
        });
      });
    });

    describe("dayjs", () => {
      it("events with correct types", async () => {
        const unique_id = v4();
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, config, hass, internal }) => {
          const entity = synapse.datetime<{ date_type: "dayjs" }>({
            context,
            date_type: "dayjs",
            name: "test",
            unique_id,
          });
          entity.onSetValue(({ value }) => {
            expect(value).toBeInstanceOf(dayjs);
          });
          hass.socket.socketEvents.emit(
            [config.synapse.EVENT_NAMESPACE, "set_value", internal.boot.application.name].join("/"),
            { data: { unique_id } },
          );
        });
      });
      it("loads from blank", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime({
            context,
            date_type: "dayjs",
            name: "test",
          });
          expect(entity.native_value).toBeInstanceOf(dayjs);
        });
      });

      it("loads from defaulted", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime({
            context,
            date_type: "dayjs",
            name: "test",
            native_value: dayjs(TESTING_DATE),
          });
          expect(entity.native_value).toEqual(dayjs(TESTING_DATE));
        });
      });

      it("can assign and retrieve", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "dayjs" }>({
            context,
            date_type: "dayjs",
            name: "test",
            native_value: dayjs(TESTING_DATE),
          });
          const now = Date.now();
          entity.native_value = dayjs(now);
          expect(entity.native_value).toEqual(dayjs(now));
        });
      });

      it("will allow some unexpected types", async () => {
        expect.assertions(4);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "dayjs" }>({
            context,
            date_type: "dayjs",
            name: "test",
            native_value: dayjs(TESTING_DATE),
          });
          const now = Date.now();
          // @ts-expect-error it's the test
          entity.native_value = new Date(now);
          expect(entity.native_value).toEqual(dayjs(now));
          // @ts-expect-error it's the test
          entity.native_value = now;
          expect(entity.native_value).toEqual(dayjs(now));
          // @ts-expect-error it's the test
          entity.native_value = new Date(now).toISOString();
          expect(entity.native_value).toEqual(dayjs(now));
          entity.native_value = undefined;
          expect(entity.native_value).toBeInstanceOf(dayjs);
        });
      });

      it("throws for invalid types", async () => {
        expect.assertions(4);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "dayjs" }>({
            context,
            date_type: "dayjs",
            name: "test",
            native_value: dayjs(TESTING_DATE),
          });
          expect(() => {
            entity.native_value = null;
          }).toThrow();
          expect(() => {
            // @ts-expect-error it's the test
            entity.native_value = {};
          }).toThrow();
          expect(() => {
            // @ts-expect-error it's the test
            entity.native_value = Number.NaN;
          }).toThrow();
          expect(() => {
            // @ts-expect-error it's the test
            entity.native_value = new Date("invalid date string");
          }).toThrow();
        });
      });
    });

    describe("iso", () => {
      it("events with correct types", async () => {
        const unique_id = v4();
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context, config, hass, internal }) => {
          const entity = synapse.datetime<{ date_type: "iso" }>({
            context,
            date_type: "iso",
            name: "test",
            unique_id,
          });
          entity.onSetValue(({ value }) => {
            expect(value).toBeInstanceOf(String);
          });
          hass.socket.socketEvents.emit(
            [config.synapse.EVENT_NAMESPACE, "set_value", internal.boot.application.name].join("/"),
            { data: { unique_id } },
          );
        });
      });

      it("loads from blank", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime({
            context,
            date_type: "iso",
            name: "test",
          });
          expect(entity.native_value).toEqual(new Date().toISOString());
        });
      });

      it("loads from defaulted", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime({
            context,
            date_type: "iso",
            name: "test",
            native_value: TESTING_DATE,
          });
          expect(entity.native_value).toEqual(new Date(TESTING_DATE).toISOString());
        });
      });

      it("can assign and retrieve", async () => {
        expect.assertions(1);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "iso" }>({
            context,
            date_type: "iso",
            name: "test",
            native_value: TESTING_DATE,
          });
          const now = Date.now();
          entity.native_value = new Date(now).toISOString();
          expect(entity.native_value).toEqual(new Date(now).toISOString());
        });
      });

      it("will allow some unexpected types", async () => {
        expect.assertions(4);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "iso" }>({
            context,
            date_type: "iso",
            name: "test",
            native_value: TESTING_DATE,
          });
          const now = Date.now();
          // @ts-expect-error it's the test
          entity.native_value = now;
          expect(entity.native_value).toEqual(new Date(now).toISOString());
          // @ts-expect-error it's the test
          entity.native_value = new Date(now);
          expect(entity.native_value).toEqual(new Date(now).toISOString());
          // @ts-expect-error it's the test
          entity.native_value = dayjs(now);
          expect(entity.native_value).toEqual(dayjs(now).toISOString());
          entity.native_value = undefined;
          expect(entity.native_value).toEqual(new Date().toISOString());
        });
      });

      it("throws for invalid types", async () => {
        expect.assertions(3);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "iso" }>({
            context,
            name: "test",
            native_value: TESTING_DATE,
          });
          expect(() => {
            entity.native_value = null;
          }).toThrow();
          expect(() => {
            // @ts-expect-error it's the test
            entity.native_value = {};
          }).toThrow();
          expect(() => {
            entity.native_value = "invalid date string";
          }).toThrow();
        });
      });
    });

    describe("other", () => {
      it("does not affect other properties", async () => {
        expect.assertions(2);
        await synapseTestRunner.run(({ synapse, context }) => {
          const entity = synapse.datetime<{ date_type: "iso" }>({
            context,
            date_type: "iso",
            name: "test",
            native_value: TESTING_DATE,
          });
          entity.disabled = true;
          expect(entity.disabled).toBe(true);
          entity.disabled = false;
          expect(entity.disabled).toBe(false);
        });
      });
    });
  });

  it("set up up correct bus transfer events", async () => {
    const unique_id = v4();
    const events = ["set_value"];
    expect.assertions(events.length);

    await synapseTestRunner.run(({ hass, event, synapse, context, config, internal }) => {
      synapse.datetime({ context, name: "test", unique_id });
      // - run through each event
      events.forEach(name => {
        const fn = vi.fn();

        // attach listener for expected internal event
        event.on(["synapse", name, unique_id].join("/"), fn);

        // emit artificial socket event
        hass.socket.socketEvents.emit(
          [config.synapse.EVENT_NAMESPACE, name, internal.boot.application.name].join("/"),
          { data: { unique_id } },
        );

        // profit
        expect(fn).toHaveBeenCalled();
      });
    });
  });
});
