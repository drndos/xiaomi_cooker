"""Services for the Xiaomi MiIO Cooker integration."""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids
from homeassistant.helpers.target import TargetSelection
from miio import Cooker, DeviceException
import probatio as vol

from .const import ATTR_PROFILE, DOMAIN, PROFILE_PATTERN, SERVICE_START, SERVICE_STOP
from .coordinator import XiaomiCookerConfigEntry

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA_STOP = vol.Schema(cv.ENTITY_SERVICE_FIELDS)
SERVICE_SCHEMA_START = SERVICE_SCHEMA_STOP.extend(
    {
        vol.Required(ATTR_PROFILE): vol.All(
            cv.string,
            vol.Strip,
            vol.Match(
                PROFILE_PATTERN,
                msg="Profile must be a hex string of 228 or 242 characters",
            ),
        )
    }
)


async def _async_target_entries(
    hass: HomeAssistant, call: ServiceCall
) -> list[XiaomiCookerConfigEntry]:
    """Return the loaded cooker entries targeted by a service call.

    Calls without a target address every configured cooker, which keeps the
    behaviour of the former YAML based services.
    """
    loaded: list[XiaomiCookerConfigEntry] = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]

    if TargetSelection(call.data).has_any_target:
        entry_ids = await async_extract_config_entry_ids(call)
        loaded = [entry for entry in loaded if entry.entry_id in entry_ids]

    if not loaded:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_cooker_targeted"
        )
    return loaded


async def _async_send(
    hass: HomeAssistant, call: ServiceCall, command: Callable[[Cooker], object]
) -> None:
    """Send a command to every targeted cooker and refresh its state."""
    for entry in await _async_target_entries(hass, call):
        coordinator = entry.runtime_data
        try:
            await hass.async_add_executor_job(command, coordinator.cooker)
        except DeviceException as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"name": entry.title, "error": str(err)},
            ) from err
        await coordinator.async_request_refresh()


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration services."""

    async def start_service(call: ServiceCall) -> None:
        """Start cooking a profile."""
        profile: str = call.data[ATTR_PROFILE]
        await _async_send(hass, call, lambda cooker: cooker.start(profile))

    async def stop_service(call: ServiceCall) -> None:
        """Stop cooking."""
        await _async_send(hass, call, lambda cooker: cooker.stop())

    hass.services.async_register(
        DOMAIN, SERVICE_START, start_service, schema=SERVICE_SCHEMA_START
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP, stop_service, schema=SERVICE_SCHEMA_STOP
    )
