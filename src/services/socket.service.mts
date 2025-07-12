import { SECOND, TServiceParams } from "@digital-alchemy/core";
import { TUniqueId } from "@digital-alchemy/hass";

type HeartBeatPayload = {
  now: number;
  hash: string;
};

type RefreshData = { data: string };

export function SynapseSocketService({
  logger,
  lifecycle,
  hass,
  scheduler,
  config,
  context,
  synapse,
  internal,
}: TServiceParams) {
  const getIdentifier = () => internal.boot.application.name;
  const name = (a: string) => [config.synapse.EVENT_NAMESPACE, a, getIdentifier()].join("/");

  const emitted = new Set<number>();

  async function emitHeartBeat() {
    const now = Date.now();
    const hash = synapse.storage.hash();
    emitted.add(now);
    await hass.socket.fireEvent(name("heartbeat"), { hash, now } satisfies HeartBeatPayload);
    scheduler.setTimeout(() => emitted.delete(now), SECOND);
  }

  function setupHeartbeat() {
    logger.trace({ name: setupHeartbeat }, `starting heartbeat`);
    return scheduler.setInterval(
      async () => await emitHeartBeat(),
      config.synapse.HEARTBEAT_INTERVAL * SECOND,
    );
  }

  // * onPostConfig
  lifecycle.onPostConfig(() => {
    hass.socket.onEvent({
      context,
      event: name("refresh"),
      async exec({ data }: RefreshData) {
        await hass.fetch.fetch({
          method: "post",
          url: `/api/config/config_entries/entry/${data}/reload`,
        });
      },
    });
    if (config.synapse.TRACE_SIBLING_HEARTBEATS) {
      hass.socket.onEvent({
        context,
        event: name("heartbeat"),
        exec({ data }: { data: HeartBeatPayload }) {
          if (!emitted.has(data.now)) {
            logger.debug({ data }, "not my heartbeat");
          }
        },
      });
    }
    if (!config.synapse.EMIT_HEARTBEAT) {
      return;
    }
    synapse.socket.setupHeartbeat();
  });

  // * onConnect
  hass.socket.onConnect(async function onConnect() {
    if (!config.synapse.EMIT_HEARTBEAT) {
      logger.warn("heartbeat disabled");
      return;
    }
    logger.debug({ name: onConnect }, `reconnect heartbeat`);
    await emitHeartBeat();
  });

  // * onPreShutdown
  lifecycle.onPreShutdown(async () => {
    if (!config.synapse.EMIT_HEARTBEAT) {
      return;
    }
    logger.debug({ name: "onPreShutdown" }, `sending shutdown notification`);
    await hass.socket.fireEvent(name("shutdown"));
  });

  async function send(unique_id: string, data: object): Promise<void> {
    if (hass.socket.connectionState !== "connected") {
      logger.debug({ name: send }, `socket connection isn't active, not sending update event`);
      return;
    }
    if (!synapse.configure.isRegistered()) {
      logger.trace({ data, name: send, unique_id }, `skipping update: not registered`);
      return;
    }
    const entity_id = hass.idBy.unique_id(unique_id as TUniqueId);
    if (entity_id) {
      logger.trace({ entity_id, name: send }, `update`);
    } else {
      logger.warn({ data, name: send, unique_id }, `updating unregistered entity`);
    }
    await hass.socket.fireEvent(name("update"), { data, unique_id });
  }

  return { send, setupHeartbeat };
}
