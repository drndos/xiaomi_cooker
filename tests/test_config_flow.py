"""Tests for the Xiaomi MiIO Cooker config flow."""

from datetime import timedelta
from unittest.mock import MagicMock

from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from miio import DeviceException, DeviceInfo
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xiaomi_miio_cooker.const import CONF_MAC, CONF_MODEL, DOMAIN

from .conftest import HOST, MAC, MODEL, TOKEN, device_info

USER_INPUT = {CONF_HOST: HOST, CONF_TOKEN: TOKEN, CONF_NAME: "Kitchen cooker"}


async def test_user_flow(
    hass: HomeAssistant, mock_device: MagicMock, mock_cooker: MagicMock
) -> None:
    """Test a successful setup from the UI."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT | {CONF_HOST: f" {HOST} "}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kitchen cooker"
    assert result["data"] == {
        CONF_HOST: HOST,
        CONF_TOKEN: TOKEN,
        CONF_MODEL: MODEL,
        CONF_MAC: MAC,
    }
    assert result["result"].unique_id == MAC
    mock_device.assert_called_once_with(HOST, TOKEN)


@pytest.mark.parametrize(
    ("info", "error"),
    [
        (DeviceException("timeout"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
        (device_info(model="zhimi.airpurifier.m1"), "unsupported_model"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_device: MagicMock,
    mock_cooker: MagicMock,
    info: Exception | DeviceInfo,
    error: str,
) -> None:
    """Test errors are shown and the flow can recover."""
    # A side effect list raises exceptions and returns anything else.
    mock_device.return_value.info.side_effect = [info]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_device.return_value.info.side_effect = None
    mock_device.return_value.info.return_value = device_info()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_invalid_token(
    hass: HomeAssistant, mock_device: MagicMock
) -> None:
    """Test a malformed token is rejected without contacting the device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT | {CONF_TOKEN: "z" * 32}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TOKEN: "invalid_token"}
    mock_device.assert_not_called()


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_device: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test the same cooker cannot be added twice, but its host is updated."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT | {CONF_HOST: "192.168.1.99"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "192.168.1.99"


async def test_reconfigure_flow(
    hass: HomeAssistant,
    mock_device: MagicMock,
    mock_cooker: MagicMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test changing the host and token of an existing entry."""
    config_entry.add_to_hass(hass)
    new_token = "0" * 32

    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.99", CONF_TOKEN: new_token}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_HOST] == "192.168.1.99"
    assert config_entry.data[CONF_TOKEN] == new_token


async def test_reconfigure_flow_wrong_device(
    hass: HomeAssistant, mock_device: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test reconfiguring to a different cooker is refused."""
    config_entry.add_to_hass(hass)
    mock_device.return_value.info.return_value = device_info(mac="11:22:33:44:55:66")

    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.99", CONF_TOKEN: TOKEN}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert config_entry.data[CONF_HOST] == HOST


async def test_options_flow(
    hass: HomeAssistant, mock_cooker: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Test changing the update interval."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 60}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_SCAN_INTERVAL: 60}
    assert config_entry.runtime_data.update_interval == timedelta(seconds=60)


async def test_import_flow(
    hass: HomeAssistant, mock_device: MagicMock, mock_cooker: MagicMock
) -> None:
    """Test importing a legacy YAML configuration."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={
            CONF_HOST: HOST,
            CONF_TOKEN: TOKEN,
            CONF_NAME: "Rice cooker",
            CONF_SCAN_INTERVAL: timedelta(seconds=1),
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Rice cooker"
    # Intervals below the minimum are clamped.
    assert result["options"] == {CONF_SCAN_INTERVAL: 5}


async def test_import_flow_cannot_connect(
    hass: HomeAssistant, mock_device: MagicMock
) -> None:
    """Test the import aborts if the cooker is unreachable."""
    mock_device.return_value.info.side_effect = DeviceException("timeout")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={CONF_HOST: HOST, CONF_TOKEN: TOKEN},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
