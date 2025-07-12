import { TContext } from "@digital-alchemy/core";

export type OnOff = "on" | "off" | "unavailable";

export interface ISynapseBrand {
  _synapse: symbol;
}
export interface ISynapseDeviceBrand {
  _synapse_device: symbol;
}

export type TSynapseId = string & ISynapseBrand;
export type TSynapseDeviceId = string & ISynapseDeviceBrand;
export const STORAGE_BOOTSTRAP_PRIORITY = 1;

export type SynapseDescribeResponse = {
  hostname: string;
  host: string;
  title: string;
  app: string;
  device: HassDeviceMetadata;
  secondary_devices: HassDeviceMetadata[];
  unique_id: string;
  username: string;
};

export type BasicAddParams = {
  locals?: object;
  attributes?: object;
};

export type HassDeviceMetadata = {
  /**
   * A URL on which the device or service can be configured, linking to paths inside the Home Assistant UI can be done by using `homeassistant://<path>`.
   */
  configuration_url?: string;
  /**
   * The manufacturer of the device, will be overridden if `manufacturer` is set. Useful for example for an integration showing all devices on the network.
   */
  manufacturer?: string;
  /**
   * The model of the device, will be overridden if `model` is set. Useful for example for an integration showing all devices on the network.
   */
  model?: string;
  /**
   * Default name of this device, will be overridden if `name` is set. Useful for example for an integration showing all devices on the network.
   */
  name?: string;
  /**
   * The hardware version of the device.
   */
  hw_version?: string;
  /**
   * The serial number of the device. Unlike a serial number in the `identifiers` set, this does not need to be unique.
   */
  serial_number?: string;
  /**
   * The suggested name for the area where the device is located.
   *
   * Use readable name, not area id ("Living Room" not "living_room")
   */
  suggested_area?: string;
  /**
   * The firmware version of the device.
   */
  sw_version?: string;
};

export const md5ToUUID = (md5: string): string =>
  md5.includes("-")
    ? md5
    : // eslint-disable-next-line @typescript-eslint/no-magic-numbers
      `${md5.slice(0, 8)}-${md5.slice(8, 12)}-${md5.slice(12, 16)}-${md5.slice(16, 20)}-${md5.slice(20)}`;

export class SynapseEntityException extends Error {
  constructor(
    public context: TContext,
    public cause: string,
    message: string,
  ) {
    super(message);
  }
}
