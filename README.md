## 📘 Description

Welcome to the Synapse custom component for Home Assistant!

This library works with [@digital-alchemy/synapse](https://github.com/Digital-Alchemy-TS/synapse) to allow Typescript based applications to create custom entities.

- Extended docs: https://docs.digital-alchemy.app/Synapse-Extension
- Discord: https://discord.digital-alchemy.app

## 🚀 Installing Synapse

To integrate Synapse with Home Assistant, add the following to your `configuration.yaml` and choose one of the install methods
```yaml
# Add to configuration.yaml
synapse:
```

### 📦 Via HACS (Recommended)

1. Ensure you have [HACS](https://hacs.xyz/) installed in Home Assistant.
2. Open HACS from the Home Assistant sidebar.
3. Navigate to "Integrations" > "+ Explore & add repositories."
4. Search for "Digital Alchemy Synapse" and select it from the list.
5. Click "Install this repository in HACS."
6. Restart Home Assistant to apply the changes.

### 📁 Manual Installation

If you prefer or need to install the integration manually:

1. Clone or download this repository.
2. Copy the `custom_components/synapse/` directory from the repository into the `<config_dir>/custom_components/` directory of your Home Assistant installation.
3. Restart Home Assistant.

### 📚 Supported Domains

Currently, Synapse supports managing various entity types within Home Assistant, including:

- **Switches**: Toggleable entities reflecting the state of external devices or services.
- **Sensors (with attributes)**: Entities providing readings from external data sources, including associated metadata.
- **Binary Sensors**: Represent binary states (on/off) of external conditions or inputs.
- **Buttons**: Triggerable entities that execute actions within external services.
- **Scenes**: Predefined configurations that adjust multiple entities to specific states (implementation by `@digital-alchemy/automation`).

Future enhancements will expand support to additional domains, enhancing the integration's versatility and applicability to a broader range of automation scenarios.

## 📖 Usage

Once enabled, the Synapse integration automatically coordinates with the connected Node.js application to manage entities. This includes generating unique IDs, tracking history, and ensuring entities appear on dashboards and persist across Home Assistant restarts.

Switches can be manipulated via the Lovelace UI or service domain calls, just like native Home Assistant switches. Sensors follow a push model, with updates sent from the Node.js application to Home Assistant.

For more advanced automation and entity grouping, refer to `@digital-alchemy/automation`, which provides tools for creating "rooms" and managing entity states and scene activation.

## 📚 Documentation and Support

For more detailed documentation and support, visit the [GitHub repository](https://github.com/Digital-Alchemy-TS/synapse-extension). Please report any issues or feature requests there.
