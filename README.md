## 📘 Description

Welcome to the Synapse custom component for Home Assistant!

This library works with [@digital-alchemy/synapse](https://github.com/Digital-Alchemy-TS/synapse) to allow Typescript based applications to create custom entities.

- [Extended docs](https://docs.digital-alchemy.app/Synapse-Extension)
- [Discord](https://discord.gg/JkZ35Gv97Y)

### 📦 Via HACS (Recommended)

1. Ensure you have [HACS](https://hacs.xyz/) installed in Home Assistant.
2. Open HACS from the Home Assistant sidebar.
3. In the top/right corner menu of the HACS screen click "Custom repositories."
4. Add github repository: `https://github.com/Digital-Alchemy-TS/synapse-extension`
5. For type select "Integration."
6. Click ADD. Then click Cancel to dismiss window.
7. Restart Home Assistant to apply the changes.

### 📁 Manual Installation

If you prefer or need to install the integration manually:

1. Clone or download this repository.
2. Copy the `custom_components/synapse/` directory from the repository into the `<config_dir>/custom_components/` directory of your Home Assistant installation.
3. Restart Home Assistant.

## 📖 Usage

Once enabled, the Synapse integration automatically coordinates with the connected Node.js application to manage entities. This includes generating unique IDs, tracking history, and ensuring entities appear on dashboards and persist across Home Assistant restarts.

Switches can be manipulated via the Lovelace UI or service domain calls, just like native Home Assistant switches. Sensors follow a push model, with updates sent from the Node.js application to Home Assistant.

For more advanced automation and entity grouping, refer to `@digital-alchemy/automation`, which provides tools for creating "rooms" and managing entity states and scene activation.

## 📚 Documentation and Support

For more detailed documentation and support, visit the [GitHub repository](https://github.com/Digital-Alchemy-TS/synapse-extension). Please report any issues or feature requests there.
