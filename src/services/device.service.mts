import { TServiceParams } from "@digital-alchemy/core";
import { createHash } from "crypto";
import fs from "fs";
import { hostname } from "os";
import { dirname, join } from "path";
import { cwd } from "process";
import { fileURLToPath } from "url";

import { HassDeviceMetadata, md5ToUUID, TSynapseDeviceId } from "../helpers/utility.mts";

const host = hostname();

export function DeviceService({ config, lifecycle, logger, internal, synapse }: TServiceParams) {
  const { is } = internal.utils;
  let synapseVersion: string;
  const DEVICE_REGISTRY = new Map<string, HassDeviceMetadata>();

  lifecycle.onPostConfig(() => {
    synapseVersion = synapse.device.loadVersion();
  });

  function loadVersion(): string {
    if (!is.empty(synapseVersion)) {
      return synapseVersion;
    }
    const path = dirname(fileURLToPath(import.meta.url));
    const file = join(path, "..", "..", "package.json");
    if (fs.existsSync(file)) {
      logger.trace("loading package");
      try {
        const contents = fs.readFileSync(file, "utf8");
        const data = JSON.parse(contents) as { version: string };
        logger.trace({ version: data?.version }, "loaded package version");
        return data?.version;
      } catch (error) {
        logger.error(error);
      }
    }
    return undefined;
  }

  return {
    getInfo(): HassDeviceMetadata {
      return {
        manufacturer: "Digital Alchemy",
        name: internal.boot.application.name,
        sw_version: synapseVersion,
        ...config.synapse.METADATA,
      };
    },

    /**
     * Create a stable UUID to uniquely identify this app.
     *
     * source data defaults to:
     * - hostname
     * - app name
     * - cwd
     *
     * alternate data can be provided via param
     */
    id(data?: string[] | string) {
      data ??= [host, internal.boot.application.name, cwd()];
      const id = md5ToUUID(
        createHash("md5")
          .update(is.string(data) ? data : data.join("-"))
          .digest("hex"),
      );
      logger.trace({ data, id }, "generated device id");
      return id;
    },

    idList: () => [...DEVICE_REGISTRY.keys()],

    list() {
      return [...DEVICE_REGISTRY.keys()].map(unique_id => ({
        ...DEVICE_REGISTRY.get(unique_id),
        hub_id: config.synapse.METADATA_UNIQUE_ID,
        unique_id,
      }));
    },

    /**
     * override the `sw_version`
     *
     * normally loads version from package.json
     */
    loadVersion,

    register(id: string, data: HassDeviceMetadata): TSynapseDeviceId {
      DEVICE_REGISTRY.set(id, data);
      logger.trace({ data, id }, "register device");
      return id as TSynapseDeviceId;
    },

    setVersion(version: string) {
      logger.trace({ version }, "update declared version");
      synapseVersion = version;
    },
  };
}
