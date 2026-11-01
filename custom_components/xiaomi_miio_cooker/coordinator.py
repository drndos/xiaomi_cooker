"""Data update coordinator for the Xiaomi MiIO Cooker integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from miio import Cooker, DeviceException
from miio.cooker import CookerStatus, OperationMode, TemperatureHistory

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The temperature history is only available while the cooker is heating.
HEATING_MODES = {OperationMode.Running, OperationMode.AutoKeepWarm}

type XiaomiCookerConfigEntry = ConfigEntry[XiaomiCookerCoordinator]


@dataclass(frozen=True, slots=True)
class CookerData:
    """Snapshot of the cooker state."""

    status: CookerStatus
    temperature_history: TemperatureHistory | None


def operation_mode(status: CookerStatus) -> OperationMode | None:
    """Return the operation mode, or None if the device reports an unknown one."""
    try:
        return status.mode
    except ValueError:
        return None


class XiaomiCookerCoordinator(DataUpdateCoordinator[CookerData]):
    """Poll the cooker and share its state with all entities."""

    config_entry: XiaomiCookerConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: XiaomiCookerConfigEntry, cooker: Cooker
    ) -> None:
        """Initialize the coordinator."""
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.cooker = cooker

    async def _async_update_data(self) -> CookerData:
        """Fetch the latest state from the device."""
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except DeviceException as err:
            raise UpdateFailed(f"Error communicating with the cooker: {err}") from err

    def _fetch(self) -> CookerData:
        """Fetch the state. Runs in the executor because python-miio is blocking."""
        status = self.cooker.status()
        _LOGGER.debug("Got new state: %s", status)

        history = None
        if operation_mode(status) in HEATING_MODES:
            history = self.cooker.get_temperature_history()

        return CookerData(status=status, temperature_history=history)
