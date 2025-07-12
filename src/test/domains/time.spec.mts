import { v4 } from "uuid";

import { synapseTestRunner } from "../../mock/index.mts";

describe("Time", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads the correct keys from storage", async () => {
    await synapseTestRunner.run(({ synapse, context }) => {
      const spy = vi.spyOn(synapse.storage, "add");
      synapse.time({ context, name: "test" });
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          load_config_keys: ["native_value"],
        }),
      );
    });
  });

  it("set up up correct bus transfer events", async () => {
    const unique_id = v4();
    const events = ["set_value"];
    expect.assertions(events.length + 2);

    await synapseTestRunner.run(({ hass, event, synapse, context, config, internal }) => {
      const inline = vi.fn();
      const dynamic = vi.fn();
      const entity = synapse.time({ context, name: "test", set_value: inline, unique_id });
      entity.onSetValue(dynamic);
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
        expect(inline).toHaveBeenCalled();
        expect(dynamic).toHaveBeenCalled();
      });
    });
  });
});
