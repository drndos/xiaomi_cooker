"""Fixtures for the Xiaomi MiIO Cooker tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

from miio import DeviceInfo
from miio.cooker import CookerStatus, TemperatureHistory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xiaomi_miio_cooker.const import CONF_MAC, CONF_MODEL, DOMAIN

HOST = "192.168.1.20"
TOKEN = "b7c4a758c251955d2c24b1d9e41ce47d"
MAC = "aa:bb:cc:dd:ee:ff"
MODEL = "chunmi.cooker.normal2"
PROFILE = (
    "0001E10100000000000080026E10082B126E1412698CAA555555550014280A6E0C02050506"
    "050505055A14040A0C0C0D00040505060A0F086E6E20000C0A5A28036468686A00040405000"
    "00000000000010202020204040506070708001212180C1E2D2D37000000000000000000000099A5"
)

WAITING_STATUS = {
    "func": "waiting",
    "menu": "0001",
    "stage": "null",
    "temp": "29",
    "t_func": "60",
    "t_precook": "-1",
    "t_cook": "60",
    "setting": "0607",
    "delay": "05040f",
    "version": "00030017",
    "favorite": "0100",
    "custom": "ffffffffffff011effff010000001d1f",
}

RUNNING_STATUS = WAITING_STATUS | {
    "func": "running",
    "stage": "03000000ff",
    "temp": "031e0b23",
    "t_func": "39",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading the custom integration in all tests."""
    return


def device_info(model: str = MODEL, mac: str | None = MAC) -> DeviceInfo:
    """Return a python-miio device info."""
    return DeviceInfo(
        {"model": model, "mac": mac, "fw_ver": "1.2.8", "hw_ver": "esp32"}
    )


@pytest.fixture
def mock_device() -> Generator[MagicMock]:
    """Mock the python-miio device used during config flow validation."""
    with patch(
        "custom_components.xiaomi_miio_cooker.config_flow.Device", autospec=True
    ) as device:
        device.return_value.info.return_value = device_info()
        yield device


@pytest.fixture
def mock_cooker() -> Generator[MagicMock]:
    """Mock the python-miio cooker used by the config entry."""
    with patch("custom_components.xiaomi_miio_cooker.Cooker", autospec=True) as cooker:
        cooker.return_value.status.return_value = CookerStatus(WAITING_STATUS)
        cooker.return_value.get_temperature_history.return_value = TemperatureHistory(
            "161515161c242a"
        )
        yield cooker.return_value


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for a cooker."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Xiaomi Miio Cooker",
        unique_id=MAC,
        data={
            "host": HOST,
            "token": TOKEN,
            CONF_MODEL: MODEL,
            CONF_MAC: MAC,
        },
    )
