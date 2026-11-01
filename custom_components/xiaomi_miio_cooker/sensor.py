"""Xiaomi MiIO Cooker sensor platform."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MAC, CONF_MODEL, DOMAIN
from .coordinator import (
    HEATING_MODES,
    CookerData,
    XiaomiCookerConfigEntry,
    XiaomiCookerCoordinator,
    operation_mode,
)

# Entities only read coordinator data, so updates need no parallelism limit.
PARALLEL_UPDATES = 0


def _mode(data: CookerData) -> str | None:
    """Return the operation mode name, falling back to the raw device value."""
    mode = operation_mode(data.status)
    return mode.name if mode is not None else data.status.data.get("func")


def _temperature(data: CookerData) -> int | None:
    """Return the most recent temperature reading.

    While heating, the temperature history is fresher than the status property.
    """
    history = data.temperature_history
    if (
        operation_mode(data.status) in HEATING_MODES
        and history
        and history.temperatures
    ):
        return history.temperatures[-1]
    return data.status.temperature


def _stage(attribute: str) -> Callable[[CookerData], StateType]:
    """Return an accessor for an attribute of the current cooking stage."""

    def value(data: CookerData) -> StateType:
        stage = data.status.stage
        if stage is None:
            return None
        result = getattr(stage, attribute)
        return result.name if isinstance(result, Enum) else result

    return value


@dataclass(frozen=True, kw_only=True)
class XiaomiCookerSensorEntityDescription(SensorEntityDescription):
    """Describes a cooker sensor."""

    value_fn: Callable[[CookerData], StateType]


SENSOR_TYPES: tuple[XiaomiCookerSensorEntityDescription, ...] = (
    XiaomiCookerSensorEntityDescription(
        key="mode",
        translation_key="mode",
        value_fn=_mode,
    ),
    XiaomiCookerSensorEntityDescription(
        key="menu",
        translation_key="menu",
        value_fn=lambda data: data.status.menu,
    ),
    XiaomiCookerSensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=_temperature,
    ),
    XiaomiCookerSensorEntityDescription(
        key="remaining",
        translation_key="remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda data: data.status.remaining,
    ),
    XiaomiCookerSensorEntityDescription(
        key="duration",
        translation_key="duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda data: data.status.duration,
    ),
    XiaomiCookerSensorEntityDescription(
        key="favorite",
        translation_key="favorite",
        value_fn=lambda data: data.status.favorite,
    ),
    XiaomiCookerSensorEntityDescription(
        key="state",
        translation_key="state",
        value_fn=_stage("state"),
    ),
    XiaomiCookerSensorEntityDescription(
        key="rice_id",
        translation_key="rice_id",
        value_fn=_stage("rice_id"),
    ),
    XiaomiCookerSensorEntityDescription(
        key="taste",
        translation_key="taste",
        value_fn=_stage("taste"),
    ),
    XiaomiCookerSensorEntityDescription(
        key="taste_phase",
        translation_key="taste_phase",
        value_fn=_stage("taste_phase"),
    ),
    XiaomiCookerSensorEntityDescription(
        key="stage_name",
        translation_key="stage_name",
        value_fn=_stage("name"),
    ),
    XiaomiCookerSensorEntityDescription(
        key="stage_description",
        translation_key="stage_description",
        value_fn=_stage("description"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XiaomiCookerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the cooker sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        XiaomiCookerSensor(coordinator, description) for description in SENSOR_TYPES
    )


class XiaomiCookerSensor(CoordinatorEntity[XiaomiCookerCoordinator], SensorEntity):
    """Representation of a Xiaomi Cooker sensor."""

    _attr_has_entity_name = True
    entity_description: XiaomiCookerSensorEntityDescription

    def __init__(
        self,
        coordinator: XiaomiCookerCoordinator,
        description: XiaomiCookerSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        entry = coordinator.config_entry
        unique_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_id}_{description.key}"

        mac = entry.data.get(CONF_MAC)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            connections={(CONNECTION_NETWORK_MAC, mac)} if mac else set(),
            manufacturer="Xiaomi",
            model=entry.data[CONF_MODEL],
            name=entry.title,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
