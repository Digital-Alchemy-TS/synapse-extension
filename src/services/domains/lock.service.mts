import { TServiceParams } from "@digital-alchemy/core";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

export type LockConfiguration<DATA extends object> = {
  /**
   * Describes what the last change was triggered by.
   */
  changed_by?: SettableConfiguration<string, DATA>;
  /**
   * Regex for code format or None if no code is required.
   */
  code_format?: SettableConfiguration<string, DATA>;
  /**
   * Indication of whether the lock is currently locked. Used to determine state.
   */
  is_locked?: SettableConfiguration<boolean, DATA>;
  /**
   * Indication of whether the lock is currently locking. Used to determine state.
   */
  is_locking?: SettableConfiguration<boolean, DATA>;
  /**
   * Indication of whether the lock is currently unlocking. Used to determine state.
   */
  is_unlocking?: SettableConfiguration<boolean, DATA>;
  /**
   * Indication of whether the lock is currently jammed. Used to determine state.
   */
  is_jammed?: SettableConfiguration<boolean, DATA>;
  /**
   * Indication of whether the lock is currently opening. Used to determine state.
   */
  is_opening?: SettableConfiguration<boolean, DATA>;
  /**
   * Indication of whether the lock is currently open. Used to determine state.
   */
  is_open?: SettableConfiguration<boolean, DATA>;
  supported_features?: number;
  /**
   * default: true
   */
  managed?: boolean;
};

export type LockEvents = {
  lock: {
    //
  };
  unlock: {
    //
  };
  open: {
    //
  };
};

export function VirtualLock({ context, synapse, logger }: TServiceParams) {
  const generate = synapse.generator.create<LockConfiguration<object>, LockEvents>({
    bus_events: ["lock", "unlock", "open"],
    context,
    // @ts-expect-error its fine
    domain: "lock",
    load_config_keys: [
      "changed_by",
      "code_format",
      "is_locked",
      "is_locking",
      "is_unlocking",
      "is_jammed",
      "is_opening",
      "is_open",
      "supported_features",
    ],
  });

  return function <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      LockConfiguration<object>
    >,
  >({
    managed = true,
    ...options
  }: AddEntityOptions<
    LockConfiguration<DATA>,
    LockEvents,
    PARAMS["attributes"],
    PARAMS["locals"],
    DATA
  >) {
    // @ts-expect-error it's fine
    const entity = generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
    if (managed) {
      entity.onLock(({}) => {
        logger.trace("[managed] onLock");
        entity.storage.set("is_locked", true);
      });
      entity.onUnlock(({}) => {
        logger.trace("[managed] onUnlock");
        entity.storage.set("is_locked", false);
      });
      entity.onOpen(({}) => {
        logger.trace("[managed] onOpen");
        entity.storage.set("is_open", true);
      });
    }
    return entity;
  };
}
