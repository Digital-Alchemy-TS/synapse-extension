import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type AlarmControlPanelStates =
  | "disarmed"
  | "armed_home"
  | "armed_away"
  | "armed_night"
  | "armed_vacation"
  | "armed_custom_bypass"
  | "pending"
  | "arming"
  | "disarming"
  | "triggered";

export type AlarmControlPanelConfiguration<DATA extends object> = {
  state?: SettableConfiguration<AlarmControlPanelStates, DATA>;
  /**
   * Whether the code is required for arm actions.
   *
   * default: true
   */
  code_arm_required?: SettableConfiguration<boolean, DATA>;
  /**
   * One of the states listed in the code formats section.
   */
  code_format?: "number" | "text";
  /**
   * Last change triggered by.
   */
  changed_by?: SettableConfiguration<string, DATA>;
  supported_features?: number;
  /**
   * default: true
   */
  managed?: boolean;
};

export type AlarmControlPanelEvents = {
  arm_custom_bypass: { code: string };
  trigger: { code: string };
  arm_vacation: { code: string };
  arm_night: { code: string };
  arm_away: { code: string };
  arm_home: { code: string };
  alarm_disarm: { code: string };
};

export function VirtualAlarmControlPanel({ context, synapse, logger }: TServiceParams) {
  const generate = synapse.generator.create<
    AlarmControlPanelConfiguration<object>,
    AlarmControlPanelEvents
  >({
    bus_events: [
      "arm_custom_bypass",
      "trigger",
      "arm_vacation",
      "arm_night",
      "arm_away",
      "arm_home",
      "alarm_disarm",
    ],
    context,
    // @ts-expect-error its fine
    domain: "alarm_control_panel",
    load_config_keys: [
      "state",
      "code_arm_required",
      "code_format",
      "changed_by",
      "supported_features",
    ],
  });

  return function <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      AlarmControlPanelConfiguration<object>
    >,
  >({
    managed = true,
    ...options
  }: AddEntityOptions<
    AlarmControlPanelConfiguration<DATA>,
    AlarmControlPanelEvents,
    PARAMS["attributes"],
    PARAMS["locals"],
    DATA
  >) {
    // @ts-expect-error it's fine
    const entity = generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
    if (managed) {
      entity.onArmCustomBypass(() => {
        logger.trace("[managed] onArmCustomBypass");
        entity.storage.set("state", "armed_away");
      });
      entity.onTrigger(() => {
        logger.trace("[managed] onTrigger");
        entity.storage.set("state", "triggered");
      });
      entity.onArmVacation(() => {
        logger.trace("[managed] onArmVacation");
        entity.storage.set("state", "armed_vacation");
      });
      entity.onArmNight(() => {
        logger.trace("[managed] onArmNight");
        entity.storage.set("state", "armed_night");
      });
      entity.onArmAway(() => {
        logger.trace("[managed] onArmAway");
        entity.storage.set("state", "armed_away");
      });
      entity.onArmHome(() => {
        logger.trace("[managed] onArmHome");
        entity.storage.set("state", "armed_home");
      });
      entity.onAlarmDisarm(() => {
        logger.trace("[managed] onAlarmDisarm");
        entity.storage.set("state", "disarmed");
      });
    }
    return entity;
  };
}
