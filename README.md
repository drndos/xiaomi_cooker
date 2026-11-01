# Xiaomi Mi Electric Rice Cooker

![GitHub actions](https://github.com/syssi/xiaomi_cooker/actions/workflows/tests.yaml/badge.svg)
![GitHub stars](https://img.shields.io/github/stars/syssi/xiaomi_cooker)
![GitHub forks](https://img.shields.io/github/forks/syssi/xiaomi_cooker)
![GitHub watchers](https://img.shields.io/github/watchers/syssi/xiaomi_cooker)
[!["Buy Me A Coffee"](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://www.buymeacoffee.com/syssi)

This is a custom component for home assistant to integrate the Xiaomi Mi Electric Rice Cooker V2.

Please follow the instructions on [Retrieving the Access Token](https://www.home-assistant.io/integrations/xiaomi_miio/#xiaomi-cloud-tokens-extractor) to get the API token of your cooker.

Credits: Thanks to [Rytilahti](https://github.com/rytilahti/python-miio) for all the work.

## Supported devices

| Name                      | Model                  | Model no. |
| ------------------------- | ---------------------- | --------- |
|                           | chunmi.cooker.normal1  | IHFB01CM  |
| Mi IH Rice Cooker         | chunmi.cooker.normal2  | IHFB01CM, 2016DP1293  |
|                           | chunmi.cooker.normal3  | |
|                           | chunmi.cooker.normal4  | |
|                           | chunmi.cooker.normal5  | |
| Mi Smart Pressure Cooker  | chunmi.cooker.press1   | YLIH01CM  |
|                           | chunmi.cooker.press2   | |

## Features

### Rice Cooker V2

* Start cooking a profile
* Stop cooking
* Sensors
  - mode
  - menu
  - temperature
  - remaining
  - duration
  - favorite
  - state (available while cooking)
  - rice_id (available while cooking)
  - taste (available while cooking)
  - taste_phase (available while cooking)
  - stage_name (available while cooking)
  - stage_description (available while cooking)
* Switches
  - TODO: Start/Stop is possible if a default profile is available (Recipe input_select?)
  - TODO: Buzzer on/off
  - TODO: Turn off the backlight on idle
* Chart
  - TODO: Temperature History (Like the temperature chart of the weather forecast)
* Services
  - TODO: stop_outdated_firmware
  - TODO: set_no_warnings / set_acknowledge
  - TODO: set_interaction
  - TODO: set_menu
  - TODO: get_temperature_history


## Install

You can install this custom component by adding this repository ([https://github.com/syssi/xiaomi_cooker](https://github.com/syssi/xiaomi_cooker/)) to [HACS](https://hacs.xyz/) in the settings menu of HACS first. You will find the custom component in the integration menu afterwards, look for 'Xiaomi Mi Electric Rice Cooker Integration'. Alternatively, you can install it manually by copying the custom_component folder to your Home Assistant configuration folder.


## Setup

Home Assistant 2026.10 or newer is required.

1. Go to **Settings → Devices & services** and click **Add integration**.
2. Search for **Xiaomi Mi Electric Rice Cooker**.
3. Enter the IP address and the 32 character token of your cooker. The name is used as the device name and as the prefix of the entity IDs, so keep the default `Xiaomi Miio Cooker` if you want the entity IDs used in the examples below.

The cooker has to be reachable while you add it, because the model and MAC address are read from the device. Each cooker is added as its own device, so multiple cookers are supported.

To change the IP address or the token later, open the integration and choose **Reconfigure**. The polling interval (default 30 seconds) can be changed in the integration **options**.

### Migrating from configuration.yaml

An existing `xiaomi_miio_cooker:` entry in `configuration.yaml` is imported automatically on the next restart. Afterwards a repair issue asks you to remove the YAML entry. If the import fails, for example because the cooker was offline, a repair issue explains why and the import is retried on the next restart. The `model` option is no longer used, the model is always detected.

The entity IDs now derive from the device name. They stay the same (`sensor.xiaomi_miio_cooker_*`) if the cooker is named `Xiaomi Miio Cooker`; with another name, update your dashboards and automations.

### Template switch example

```yaml
# configuration.yaml

# template switch example to start a specific cooking profile
switch:
  - platform: template
    switches:
      xiaomi_miio_cooker:
        value_template: "{{ is_state('sensor.xiaomi_miio_cooker_mode', 'Running') }}"
        turn_on:
          action: xiaomi_miio_cooker.start
          data:
            profile: "0001E10100000000000080026E10082B126E1412698CAA555555550014280A6E0C02050506050505055A14040A0C0C0D00040505060A0F086E6E20000C0A5A28036468686A0004040500000000000000010202020204040506070708001212180C1E2D2D37000000000000000000000099A5"
        turn_off:
          action: xiaomi_miio_cooker.stop
```

## Lovelace

```
type: vertical-stack
cards:
  - type: entities
    title: Ricecooker
    state_color: false
    entities:
      - entity: switch.xiaomi_miio_cooker
      - entity: sensor.xiaomi_miio_cooker_duration
      - entity: sensor.xiaomi_miio_cooker_remaining
      - entity: sensor.xiaomi_miio_cooker_mode
        secondary_info: last-changed
      - entity: sensor.xiaomi_miio_cooker_stage_name
        secondary_info: last-changed
      - entity: sensor.xiaomi_miio_cooker_stage_description
      - entity: sensor.xiaomi_miio_cooker_rice_id
      - entity: sensor.xiaomi_miio_cooker_state
        secondary_info: last-changed
      - entity: sensor.xiaomi_miio_cooker_taste
      - entity: sensor.xiaomi_miio_cooker_taste_phase
      - entity: sensor.xiaomi_miio_cooker_temperature
      - entity: sensor.xiaomi_miio_cooker_favorite
      - entity: sensor.xiaomi_miio_cooker_menu
        secondary_info: last-changed
  - type: sensor
    entity: sensor.xiaomi_miio_cooker_remaining
    detail: 2
    hours_to_show: 1
  - type: sensor
    entity: sensor.xiaomi_miio_cooker_temperature
    graph: line
    detail: 2
    hours_to_show: 2
```

![Lovelace card example](lovelace-card-example.png "lovelace card")

If you prefer a button instead of a switch entity you could add a lovelace button card to you dashboard:

```
type: button
tap_action:
  action: perform-action
  perform_action: xiaomi_miio_cooker.start
  data:
    profile: "010088003201000028000012000000000000000000000846822A6E14002018000F6E82736E140A201810000000000000000000003C8782716E1400200A100000000000000000000000000000000000000000000000000000000000003C0A000000008700000000000000000000000000424D"
hold_action:
  action: more-info
show_icon: true
show_name: true
icon: 'mdi:cake'
name: Baking Cake
icon_height: 40px
```

![Lovelace button to start cooking](lovelace-button-start-cooking.png "lovelace button")

## Debugging

If the custom component doesn't work out of the box for your device please update your configuration to increase the log level:

```
logger:
  default: warn
  logs:
    custom_components.xiaomi_miio_cooker: debug
    miio: debug
```

## Services

Both services accept an optional target (entity, device or area). Without a target the command is sent to every configured cooker.

#### Service `xiaomi_miio_cooker.start`

Start cooking a profile.

| Service data attribute    | Optional | Description                                                          |
|---------------------------|----------|----------------------------------------------------------------------|
| `profile`                 |       no | Hex encoded profile (228 or 242 characters) which describes the temperature curve. |

Some cooking profile examples: https://raw.githubusercontent.com/rytilahti/python-miio/master/miio/data/cooker_profiles.json

- `MODEL_PRESSURE`: `chunmi.cooker.press1`, `chunmi.cooker.press2`
- `MODEL_NORMAL_GROUP1`: `chunmi.cooker.normal2`, `chunmi.cooker.normal5`
- `MODEL_NORMAL_GROUP2`: `chunmi.cooker.normal3`, `chunmi.cooker.normal4`

#### Service `xiaomi_miio_cooker.stop`

Stop the cooking process.

## Development

Home Assistant only runs on Linux and macOS, so run the tests there or in a container:

```bash
pip install --require-hashes -r requirements_test.txt
pytest
```

### Supply chain

Everything CI downloads is pinned to content that can't change underneath it:

- GitHub Actions and pre-commit hooks are pinned to commit SHAs, each verified against the upstream release tag noted in the comment next to it.
- Python packages are installed from hash-locked `requirements_*.txt` files. Edit the matching `.in` file and regenerate the lock:

  ```bash
  uv pip compile requirements_test.in --universal --python-version 3.14.2 --generate-hashes --no-header -o requirements_test.txt
  uv pip compile requirements_lint.in --universal --python-version 3.14 --generate-hashes --no-header -o requirements_lint.txt
  ```

- The HACS and hassfest Docker images are pinned by digest. Dependabot doesn't update these, so refresh them by hand with `docker buildx imagetools inspect ghcr.io/hacs/action:main` and `docker buildx imagetools inspect ghcr.io/home-assistant/hassfest:latest`.
- Workflows run with a read-only token and don't keep it in the checkout.
- Dependabot proposes updates only after a release has been public for 7 days.
