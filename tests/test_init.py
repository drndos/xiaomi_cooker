"""Tests for the Xiaomi MiIO Cooker setup, sensors and services."""

from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    STATE_UNAVAILABLE,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from miio import DeviceException
from miio.cooker import CookerStatus
import probatio as vol
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xiaomi_miio_cooker.const import (
    ATTR_PROFILE,
    DOMAIN,
    SERVICE_START,
    SERVICE_STOP,
)

from .conftest import HOST, MAC, PROFILE, RUNNING_STATUS, TOKEN


def _cooker_device(hass: HomeAssistant, entry: MockConfigEntry) -> dr.DeviceEntry:
    """Return the cooker device of a config entry."""
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, MAC), entry.entry_id
    )
    assert device is not None
    return device


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_and_unload(
    hass: HomeAssistant, mock_cooker: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test the entry sets up its sensors and unloads cleanly."""
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    # Entity IDs match the ones created by the former YAML setup.
    assert hass.states.get("sensor.xiaomi_miio_cooker_mode").state == "Waiting"
    assert hass.states.get("sensor.xiaomi_miio_cooker_menu").state == "1"
    assert hass.states.get("sensor.xiaomi_miio_cooker_temperature").state == "29"
    assert hass.states.get("sensor.xiaomi_miio_cooker_remaining").state == "60"
    assert hass.states.get("sensor.xiaomi_miio_cooker_stage_name").state == "unknown"

    device = _cooker_device(hass, config_entry)
    assert device.model == "chunmi.cooker.normal2"
    mock_cooker.get_temperature_history.assert_not_called()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_when_offline(
    hass: HomeAssistant, mock_cooker: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test the setup is retried if the cooker cannot be reached."""
    mock_cooker.status.side_effect = DeviceException("timeout")
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_running_state(
    hass: HomeAssistant, mock_cooker: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test the sensors while cooking and when the device drops off."""
    await _setup(hass, config_entry)

    mock_cooker.status.return_value = CookerStatus(RUNNING_STATUS)
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.xiaomi_miio_cooker_mode").state == "Running"
    # Latest value of the temperature history 0x2a.
    assert hass.states.get("sensor.xiaomi_miio_cooker_temperature").state == "42"
    assert hass.states.get("sensor.xiaomi_miio_cooker_state").state == "3"
    assert hass.states.get("sensor.xiaomi_miio_cooker_stage_name").state != "unknown"

    # Polling the same history again must not consume it.
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.xiaomi_miio_cooker_temperature").state == "42"

    mock_cooker.status.side_effect = DeviceException("timeout")
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.xiaomi_miio_cooker_mode").state == STATE_UNAVAILABLE


async def test_unknown_mode(
    hass: HomeAssistant, mock_cooker: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test an unknown operation mode doesn't break the update."""
    mock_cooker.status.return_value = CookerStatus(
        RUNNING_STATUS | {"func": "brandnew"}
    )
    await _setup(hass, config_entry)

    assert hass.states.get("sensor.xiaomi_miio_cooker_mode").state == "brandnew"
    assert hass.states.get("sensor.xiaomi_miio_cooker_temperature").state == "unknown"


async def test_services(
    hass: HomeAssistant, mock_cooker: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test the start and stop services."""
    await _setup(hass, config_entry)

    await hass.services.async_call(
        DOMAIN, SERVICE_START, {ATTR_PROFILE: PROFILE}, blocking=True
    )
    mock_cooker.start.assert_called_once_with(PROFILE)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_STOP,
        {ATTR_ENTITY_ID: "sensor.xiaomi_miio_cooker_mode"},
        blocking=True,
    )
    mock_cooker.stop.assert_called_once_with()

    device = _cooker_device(hass, config_entry)
    await hass.services.async_call(
        DOMAIN, SERVICE_STOP, {ATTR_DEVICE_ID: device.id}, blocking=True
    )
    assert mock_cooker.stop.call_count == 2

    area = ar.async_get(hass).async_create("Kitchen")
    dr.async_get(hass).async_update_device(device.id, area_id=area.id)
    await hass.services.async_call(
        DOMAIN, SERVICE_STOP, {ATTR_AREA_ID: area.id}, blocking=True
    )
    assert mock_cooker.stop.call_count == 3


@pytest.mark.parametrize(
    "profile",
    [
        "too short",
        PROFILE[:-1] + "Z",
        PROFILE + "00",
    ],
)
async def test_start_rejects_invalid_profile(
    hass: HomeAssistant,
    mock_cooker: MagicMock,
    config_entry: MockConfigEntry,
    profile: str,
) -> None:
    """Test malformed profiles never reach the device."""
    await _setup(hass, config_entry)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, SERVICE_START, {ATTR_PROFILE: profile}, blocking=True
        )
    mock_cooker.start.assert_not_called()


async def test_service_errors(
    hass: HomeAssistant, mock_cooker: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test device errors and unmatched targets are reported."""
    await _setup(hass, config_entry)

    mock_cooker.stop.side_effect = DeviceException("timeout")
    with pytest.raises(HomeAssistantError, match="timeout"):
        await hass.services.async_call(DOMAIN, SERVICE_STOP, {}, blocking=True)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_STOP,
            {ATTR_ENTITY_ID: "sensor.not_a_cooker"},
            blocking=True,
        )


async def test_yaml_import(
    hass: HomeAssistant, mock_device: MagicMock, mock_cooker: MagicMock
) -> None:
    """Test a YAML configuration is imported and flagged as deprecated."""
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: {"host": HOST, "token": TOKEN}}
    )
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED
    assert ir.async_get(hass).async_get_issue(
        HOMEASSISTANT_DOMAIN, f"deprecated_yaml_{DOMAIN}"
    )


async def test_yaml_import_failure(
    hass: HomeAssistant, mock_device: MagicMock, mock_cooker: MagicMock
) -> None:
    """Test a failed YAML import raises a repair issue."""
    mock_device.return_value.info.side_effect = DeviceException("timeout")
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: {"host": HOST, "token": TOKEN}}
    )
    await hass.async_block_till_done()

    assert not hass.config_entries.async_entries(DOMAIN)
    assert ir.async_get(hass).async_get_issue(
        DOMAIN, "deprecated_yaml_import_issue_cannot_connect"
    )
