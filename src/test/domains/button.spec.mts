import { v4 } from "uuid";

import { synapseTestRunner } from "../../mock/index.mts";

describe("Button", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads the correct keys from storage", async () => {
    expect.assertions(1);
    await synapseTestRunner.run(({ synapse, context }) => {
      const spy = vi.spyOn(synapse.storage, "add");
      synapse.button({ context, name: "test" });
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          load_config_keys: ["device_class"],
        }),
      );
    });
  });

  it("set up up correct bus transfer events", async () => {
    const unique_id = v4();
    const events = ["press"];
    expect.assertions(events.length);

    await synapseTestRunner.run(({ hass, event, synapse, context, config, internal }) => {
      synapse.button({ context, name: "test", unique_id });
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
