import { TServiceParams } from "@digital-alchemy/core";
import { hostname, userInfo } from "os";
import { gzipSync } from "zlib";

export function DiscoveryService({
  config,
  lifecycle,
  logger,
  context,
  internal,
  hass,
  synapse,
}: TServiceParams) {
  // * Raw data payload
  const APP_METADATA = () => ({
    app: internal.boot.application.name,
    device: synapse.device.getInfo(),
    hash: synapse.storage.hash(),
    hostname: hostname(),
    secondary_devices: synapse.device.list(),
    title: config.synapse.METADATA_TITLE,
    unique_id: config.synapse.METADATA_UNIQUE_ID,
    username: userInfo().username,
    ...synapse.storage.dump(),
  });

  // * Build the compressed version
  const payload = () => gzipSync(JSON.stringify(APP_METADATA())).toString("hex");

  // * Set up event listeners for hass reloads
  lifecycle.onPostConfig(() => {
    const { EVENT_NAMESPACE } = config.synapse;
    const { name } = internal.boot.application;
    // * Discover all
    hass.socket.onEvent({
      context,
      event: `${EVENT_NAMESPACE}/discovery`,
      async exec() {
        if (synapse.configure.isRegistered()) {
          logger.debug({ name: "discovery" }, `received global discovery request, ignoring`);
          return;
        }
        logger.info({ name: "discovery" }, `global discovery`);
        await hass.socket.fireEvent(`${EVENT_NAMESPACE}/identify`, { compressed: payload() });
      },
    });

    // * Specific identify
    hass.socket.onEvent({
      context,
      event: `${EVENT_NAMESPACE}/discovery/${name}`,
      async exec() {
        logger.info({ name: "discovery" }, `app discovery`);
        await hass.socket.fireEvent(`${EVENT_NAMESPACE}/identify/${name}`, {
          compressed: payload(),
        });
      },
    });
  });

  return { APP_METADATA };
}
