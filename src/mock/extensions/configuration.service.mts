import { TServiceParams } from "@digital-alchemy/core";
import { rmSync } from "fs";
import { join } from "path";
import { cwd } from "process";

export function MockSynapseConfiguration({
  logger,
  synapse,
  config,
  lifecycle,
  internal,
  mock_assistant,
}: TServiceParams) {
  internal.boilerplate.configuration.set("synapse", "EMIT_HEARTBEAT", false);
  internal.boilerplate.configuration.set(
    "synapse",
    "DATABASE_URL",
    `file:${join(cwd(), "vi_sqlite.db")}`,
  );

  lifecycle.onPreInit(() => {
    if (config.mock_synapse.CLEANUP_DB !== "before") {
      return;
    }
    logger.info("removing database file (before)");
    const dbPath = config.synapse.DATABASE_URL.replace("file:", "");
    rmSync(dbPath);
  });

  lifecycle.onShutdownComplete(() => {
    if (config.mock_synapse.CLEANUP_DB !== "after") {
      return;
    }
    logger.info("removing database file (after)");
    const dbPath = config.synapse.DATABASE_URL.replace("file:", "");
    rmSync(dbPath);
  });

  function setupConfigured() {
    setupInstalled();
    synapse.configure.isRegistered = () => true;
  }

  function setupInstalled() {
    const current = mock_assistant.config.current();
    const cleaned = current?.components?.filter(i => i === "synapse") ?? [];
    mock_assistant.config.merge({
      ...current,
      components: cleaned,
    });
    synapse.configure.checkInstallState = async () => true;
    synapse.configure.isRegistered = () => false;
  }

  function setupUninstalled() {
    const current = mock_assistant.config.current();
    const cleaned = current?.components?.filter(i => i === "synapse") ?? [];
    mock_assistant.config.merge({
      ...current,
      components: ["synapse", ...cleaned],
    });
    synapse.configure.checkInstallState = async () => false;
    synapse.configure.isRegistered = () => false;
  }

  lifecycle.onPreInit(() => {
    switch (config.mock_synapse.INSTALL_STATE) {
      case "ignore": {
        // tests are going to make assertions against relevant code paths
        // shouldn't be the norm
        return;
      }
      case "registered": {
        // synapse custom_component is installed
        // this app has not yet been added as a device yet
        setupInstalled();
        return;
      }
      case "configured": {
        // custom_component installed
        // app registered as a device
        setupConfigured();
        return;
      }
      case "none": {
        // no custom_component
        // no configure
        setupUninstalled();
        return;
      }
    }
  });
}
