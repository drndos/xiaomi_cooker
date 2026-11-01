"""Xiaomi MiIO Cooker integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    Platform,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType
from miio import Cooker
import probatio as vol

from .const import (
    CONF_MODEL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SUPPORTED_MODELS,
)
from .coordinator import XiaomiCookerConfigEntry, XiaomiCookerCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

# Legacy configuration.yaml support. The entry is imported into a config entry.
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_TOKEN): vol.All(
                    cv.string, vol.Length(min=32, max=32)
                ),
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Optional(CONF_MODEL): vol.In(SUPPORTED_MODELS),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration and import a legacy YAML configuration."""
    async_setup_services(hass)

    if DOMAIN in config:
        hass.async_create_task(_async_import_yaml(hass, config[DOMAIN]))

    return True


async def _async_import_yaml(hass: HomeAssistant, conf: ConfigType) -> None:
    """Import the YAML configuration and raise a repair issue."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
    )

    if (
        result["type"] is FlowResultType.ABORT
        and result["reason"] != "already_configured"
    ):
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"deprecated_yaml_import_issue_{result['reason']}",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.WARNING,
            translation_key=f"deprecated_yaml_import_issue_{result['reason']}",
            translation_placeholders={"host": conf[CONF_HOST]},
        )
        return

    ir.async_create_issue(
        hass,
        HOMEASSISTANT_DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={
            "domain": DOMAIN,
            "integration_title": "Xiaomi Mi Electric Rice Cooker",
        },
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: XiaomiCookerConfigEntry
) -> bool:
    """Set up the cooker from a config entry."""
    cooker = Cooker(
        entry.data[CONF_HOST], entry.data[CONF_TOKEN], model=entry.data[CONF_MODEL]
    )
    coordinator = XiaomiCookerCoordinator(hass, entry, cooker)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: XiaomiCookerConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
