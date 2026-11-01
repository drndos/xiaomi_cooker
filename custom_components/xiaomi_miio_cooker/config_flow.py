"""Config flow for the Xiaomi MiIO Cooker integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from miio import Device, DeviceException
import probatio as vol

from .const import (
    CONF_MAC,
    CONF_MODEL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SUPPORTED_MODELS,
    TOKEN_PATTERN,
)
from .coordinator import XiaomiCookerConfigEntry

_LOGGER = logging.getLogger(__name__)

TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


@dataclass(frozen=True, slots=True)
class DeviceDetails:
    """Details reported by the cooker during validation."""

    model: str
    mac: str | None


class CannotConnectError(Exception):
    """Error to indicate we cannot connect to the device."""


class UnsupportedModelError(Exception):
    """Error to indicate the device is not a supported cooker."""

    def __init__(self, model: str) -> None:
        """Initialize the error."""
        super().__init__(model)
        self.model = model


def _fetch_device_details(host: str, token: str) -> DeviceDetails:
    """Connect to the device and read its model. Runs in the executor."""
    try:
        info = Device(host, token).info()
    except DeviceException as err:
        raise CannotConnectError from err

    _LOGGER.debug(
        "%s %s %s detected", info.model, info.firmware_version, info.hardware_version
    )
    if info.model not in SUPPORTED_MODELS:
        raise UnsupportedModelError(info.model)

    return DeviceDetails(
        model=info.model, mac=format_mac(info.mac_address) if info.mac_address else None
    )


class XiaomiCookerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Xiaomi MiIO Cooker."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: XiaomiCookerConfigEntry,
    ) -> XiaomiCookerOptionsFlow:
        """Get the options flow for this handler."""
        return XiaomiCookerOptionsFlow()

    async def _async_validate(
        self, host: str, token: str, errors: dict[str, str], placeholders: dict
    ) -> DeviceDetails | None:
        """Validate the user input, filling errors on failure."""
        if not TOKEN_PATTERN.fullmatch(token):
            errors[CONF_TOKEN] = "invalid_token"
            return None

        try:
            return await self.hass.async_add_executor_job(
                _fetch_device_details, host, token
            )
        except CannotConnectError:
            errors["base"] = "cannot_connect"
        except UnsupportedModelError as err:
            errors["base"] = "unsupported_model"
            placeholders["model"] = err.model
        except Exception:
            _LOGGER.exception("Unexpected exception while validating the cooker")
            errors["base"] = "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            token = user_input[CONF_TOKEN].strip()
            details = await self._async_validate(host, token, errors, placeholders)
            if details is not None:
                await self.async_set_unique_id(details.mac or host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_HOST: host,
                        CONF_TOKEN: token,
                        CONF_MODEL: details.model,
                        CONF_MAC: details.mac,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_TOKEN): TOKEN_SELECTOR,
                        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    }
                ),
                user_input,
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow the user to change the host or token of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            token = user_input[CONF_TOKEN].strip()
            details = await self._async_validate(host, token, errors, placeholders)
            if details is not None:
                # Without a MAC the unique ID is the old host, which can't be checked.
                if details.mac is not None:
                    await self.async_set_unique_id(details.mac)
                    self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_TOKEN: token,
                        CONF_MODEL: details.model,
                        CONF_MAC: details.mac,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_TOKEN): TOKEN_SELECTOR,
                    }
                ),
                user_input or {CONF_HOST: entry.data[CONF_HOST]},
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_import(
        self, import_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Import a legacy configuration.yaml entry."""
        host = import_data[CONF_HOST]
        token = import_data[CONF_TOKEN]
        errors: dict[str, str] = {}
        details = await self._async_validate(host, token, errors, {})
        if details is None:
            return self.async_abort(reason=errors.get("base", "invalid_token"))

        await self.async_set_unique_id(details.mac or host)
        self._abort_if_unique_id_configured()

        options = {}
        if (scan_interval := import_data.get(CONF_SCAN_INTERVAL)) is not None:
            options[CONF_SCAN_INTERVAL] = min(
                max(scan_interval.total_seconds(), MIN_SCAN_INTERVAL),
                MAX_SCAN_INTERVAL,
            )

        return self.async_create_entry(
            title=import_data.get(CONF_NAME, DEFAULT_NAME),
            data={
                CONF_HOST: host,
                CONF_TOKEN: token,
                CONF_MODEL: details.model,
                CONF_MAC: details.mac,
            },
            options=options,
        )


class XiaomiCookerOptionsFlow(OptionsFlowWithReload):
    """Handle the options of an existing entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_SCAN_INTERVAL): NumberSelector(
                            NumberSelectorConfig(
                                min=MIN_SCAN_INTERVAL,
                                max=MAX_SCAN_INTERVAL,
                                step=1,
                                mode=NumberSelectorMode.BOX,
                                unit_of_measurement="s",
                            )
                        ),
                    }
                ),
                {
                    CONF_SCAN_INTERVAL: self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
                    )
                },
            ),
        )
