import { Dayjs } from "dayjs";

import { EntityConfigCommon, SettableConfiguration } from "./common-config.mts";

type DurationSensor = {
  device_class: "duration";

  unit_of_measurement: "h" | "min" | "s" | "d";
};

type TemperatureSensor = {
  device_class: "temperature";

  unit_of_measurement: "K" | "°C" | "°F";
};

type Precipitation = {
  device_class: "precipitation";

  unit_of_measurement: "cm" | "in" | "mm";
};

type ApparentPowerSensor = {
  device_class: "apparent_power";

  unit_of_measurement: "VA";
};

type WaterSensor = {
  device_class: "water";

  unit_of_measurement: "L" | "gal" | "m³" | "ft³" | "CCF";
};

type WeightSensor = {
  device_class: "weight";

  unit_of_measurement: "kg" | "g" | "mg" | "µg" | "oz" | "lb" | "st";
};

type WindSpeedSensor = {
  device_class: "wind_speed";

  unit_of_measurement: "ft/s" | "km/h" | "kn" | "m/s" | "mph";
};

type SpeedSensor = {
  device_class: "speed";

  unit_of_measurement: "ft/s" | "in/d" | "in/h" | "km/h" | "kn" | "m/s" | "mph" | "mm/d";
};

type VoltageSensor = {
  device_class: "voltage";

  unit_of_measurement: "V" | "mV";
};

type SignalStrengthSensor = {
  device_class: "signal_strength";

  unit_of_measurement: "dB" | "dBm";
};

type VolumeSensor = {
  device_class: "volume";

  unit_of_measurement: "L" | "mL" | "gal" | "fl. oz." | "m³" | "ft³" | "CCF";
};

type SoundPressureSensor = {
  device_class: "sound_pressure";

  unit_of_measurement: "dB" | "dBA";
};

type PressureSensor = {
  device_class: "pressure";

  unit_of_measurement: "cbar" | "bar" | "hPa" | "inHg" | "kPa" | "mbar" | "Pa" | "psi";
};

type ReactivePowerSensor = {
  device_class: "reactive_power";

  unit_of_measurement: "var";
};

type PrecipitationIntensitySensor = {
  device_class: "precipitation_intensity";

  unit_of_measurement: "in/d" | "in/h" | "mm/d" | "mm/h";
};

type PowerFactorSensor = {
  device_class: "power_factor";

  unit_of_measurement: "%" | "None";
};

type PowerSensor = {
  device_class: "power";

  unit_of_measurement: "W" | "kW";
};

type MixedGasSensor = {
  device_class:
    | "nitrogen_monoxide"
    | "nitrous_oxide"
    | "ozone"
    | "pm1"
    | "pm25"
    | "pm10"
    | "volatile_organic_compounds";

  unit_of_measurement: "µg/m³";
};

type IlluminanceSensor = {
  device_class: "illuminance";

  unit_of_measurement: "lx";
};

type IrradianceSensor = {
  device_class: "irradiance";

  unit_of_measurement: "W/m²" | "BTU/(h⋅ft²)";
};

type GasSensor = {
  device_class: "gas";

  unit_of_measurement: "m³" | "ft³" | "CCF";
};

type FrequencySensor = {
  device_class: "frequency";

  unit_of_measurement: "Hz" | "kHz" | "MHz" | "GHz";
};

type EnergySensor = {
  device_class: "energy";

  unit_of_measurement: "Wh" | "kWh" | "MWh" | "MJ" | "GJ";
};

type DistanceSensor = {
  device_class: "distance";

  unit_of_measurement: "km" | "m" | "cm" | "mm" | "mi" | "yd" | "in";
};

type MonetarySensor = {
  device_class: "monetary";
  /**
   * https://en.wikipedia.org/wiki/ISO_4217#Active_codes
   */
  unit_of_measurement: string;
};

type DataRateSensor = {
  device_class: "data_rate";

  unit_of_measurement:
    | "bit/s"
    | "kbit/s"
    | "Mbit/s"
    | "Gbit/s"
    | "B/s"
    | "kB/s"
    | "MB/s"
    | "GB/s"
    | "KiB/s"
    | "MiB/s"
    | "GiB/s";
};

type DataSizeSensor = {
  device_class: "data_size";

  unit_of_measurement:
    | "bit"
    | "kbit"
    | "Mbit"
    | "Gbit"
    | "B"
    | "kB"
    | "MB"
    | "GB"
    | "TB"
    | "PB"
    | "EB"
    | "ZB"
    | "YB"
    | "KiB"
    | "MiB"
    | "GiB"
    | "TiB"
    | "PiB"
    | "EiB"
    | "ZiB"
    | "YiB";
};

type AtmosphericPressureSensor = {
  device_class: "atmospheric_pressure";

  unit_of_measurement: "cbar" | "bar" | "hPa" | "inHg" | "kPa" | "mbar" | "Pa" | "psi";
};

type CurrentSensor = {
  device_class: "current";

  unit_of_measurement: "A" | "mA";
};

type CarbonSensor = {
  device_class: "carbon_dioxide" | "carbon_monoxide";
  unit_of_measurement: "ppm";
};

type PercentSensor = {
  device_class: "battery" | "humidity" | "moisture";
  unit_of_measurement: "%";
};

type DateSensor = {
  device_class?: "timestamp" | "date";
  sensor_type?: "date" | "iso" | "dayjs";
  unit_of_measurement?: void;
};

type AirQualitySensor = {
  device_class?: "aqi";
  unit_of_measurement?: void;
};

type OptionsSensor<STATE_TYPE> = {
  device_class?: "enum";
  sensor_type?: "string";

  /**
   * In case this sensor provides a textual state, this property can be used to provide a list of possible states.
   * Requires the enum device class to be set.
   * Cannot be combined with `state_class` or `native_unit_of_measurement`.
   */
  options?: Array<STATE_TYPE extends string ? STATE_TYPE : string>;

  unit_of_measurement?: void;
};

export const SENSOR_DEVICE_CLASS_CONFIG_KEYS = ["device_class", "unit_of_measurement"];

export enum SensorStateClass {
  /**
   * The state represents a measurement in present time, not a historical aggregation such as statistics or a prediction of the future.
   *
   * Examples of what should be classified `measurement` are: current temperature, humidity or electric power.
   *
   * Examples of what should not be classified as `measurement`: Forecasted temperature for tomorrow, yesterday's energy consumption or anything else that doesn't include the current measurement.
   *
   * For supported sensors, statistics of hourly min, max and average sensor readings is updated every 5 minutes.
   */
  MEASUREMENT = "measurement",
  /**
   * The state represents a total amount that can both increase and decrease, e.g. a net energy meter.
   * Statistics of the accumulated growth or decline of the sensor's value since it was first added is updated every 5 minutes.
   * This state class should not be used for sensors where the absolute value is interesting instead of the accumulated growth or decline, for example remaining battery capacity or CPU load; in such cases state class measurement should be used instead.
   */
  TOTAL = "total",
  /**
   * Similar to total, with the restriction that the state represents a monotonically increasing positive total which periodically restarts counting from 0, e.g. a daily amount of consumed gas, weekly water consumption or lifetime energy consumption.
   * Statistics of the accumulated growth of the sensor's value since it was first added is updated every 5 minutes.
   * A decreasing value is interpreted as the start of a new meter cycle or the replacement of the meter.
   */
  TOTAL_INCREASING = "total_increasing",
}

type MultipleUnits = (
  | AtmosphericPressureSensor
  | CurrentSensor
  | DataRateSensor
  | DataSizeSensor
  | DistanceSensor
  | DurationSensor
  | EnergySensor
  | FrequencySensor
  | GasSensor
  | PowerSensor
  | Precipitation
  | PrecipitationIntensitySensor
  | PressureSensor
  | SignalStrengthSensor
  | SoundPressureSensor
  | SpeedSensor
  | TemperatureSensor
  | VoltageSensor
  | VolumeSensor
  | WaterSensor
  | WeightSensor
  | WindSpeedSensor
) & {
  /**
   * The unit of measurement to be used for the sensor's state.
   * For sensors with a unique_id, this will be used as the initial unit of measurement, which users can then override.
   * For sensors without a unique_id, this will be the unit of measurement for the sensor's state.
   * This property is intended to be used by integrations to override automatic unit conversion rules, for example,
   * to make a temperature sensor always display in °C regardless of whether the configured unit system prefers °C or °F,
   * or to make a distance sensor always display in miles even if the configured unit system is metric.
   */
  suggested_unit_of_measurement?: string;
};

type NumberSensors = (
  | MultipleUnits
  | AirQualitySensor
  | ApparentPowerSensor
  | CarbonSensor
  | IlluminanceSensor
  | IrradianceSensor
  | MixedGasSensor
  | MonetarySensor
  | PercentSensor
  | PowerFactorSensor
  | ReactivePowerSensor
) & {
  sensor_type?: "number";

  /**
   * The number of decimals which should be used in the sensor's state when it's displayed.
   */
  suggested_display_precision?: number;

  /**
   * The time when an accumulating sensor such as an electricity usage meter, gas meter, water meter etc. was initialized.
   *
   * If the time of initialization is unknown, set it to `None`.
   *
   * Note that the `datetime.datetime` returned by the `last_reset` property will be converted to an ISO 8601-formatted string when the entity's state attributes are updated. When changing `last_reset`, the `state` must be a valid number.
   */
  last_reset?: SettableConfiguration<Dayjs, object>;

  /**
   * Type of state.
   * If not `None`, the sensor is assumed to be numerical and will be displayed as a line-chart in the frontend instead of as discrete values.
   */
  state_class?: SensorStateClass | `${SensorStateClass}`;
};

export type SensorDeviceClasses<STATE_TYPE = unknown> =
  | NumberSensors
  | DateSensor
  | OptionsSensor<STATE_TYPE>;

export type SensorConfiguration<
  ATTRIBUTES extends object,
  LOCALS extends object,
  STATE_TYPE extends string | number | Date | Dayjs,
  DATA extends object,
> = EntityConfigCommon<ATTRIBUTES, LOCALS, DATA> &
  SensorDeviceClasses<STATE_TYPE> & {
    state?: SettableConfiguration<STATE_TYPE, DATA>;
  };
