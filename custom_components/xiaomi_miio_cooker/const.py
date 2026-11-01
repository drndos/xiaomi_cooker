"""Constants for the Xiaomi MiIO Cooker integration."""

from datetime import timedelta
import re
from typing import Final

DOMAIN: Final = "xiaomi_miio_cooker"

DEFAULT_NAME: Final = "Xiaomi Miio Cooker"
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 3600

CONF_MODEL: Final = "model"
CONF_MAC: Final = "mac"

MODEL_PRESSURE1: Final = "chunmi.cooker.press1"
MODEL_PRESSURE2: Final = "chunmi.cooker.press2"
MODEL_NORMAL1: Final = "chunmi.cooker.normal1"
MODEL_NORMAL2: Final = "chunmi.cooker.normal2"
MODEL_NORMAL3: Final = "chunmi.cooker.normal3"
MODEL_NORMAL4: Final = "chunmi.cooker.normal4"
MODEL_NORMAL5: Final = "chunmi.cooker.normal5"

SUPPORTED_MODELS: Final = [
    MODEL_PRESSURE1,
    MODEL_PRESSURE2,
    MODEL_NORMAL1,
    MODEL_NORMAL2,
    MODEL_NORMAL3,
    MODEL_NORMAL4,
    MODEL_NORMAL5,
]

# The miIO token is a 128 bit key represented as 32 hex characters.
TOKEN_PATTERN: Final = re.compile(r"^[0-9a-fA-F]{32}$")

# python-miio only accepts hex encoded profiles of these lengths.
PROFILE_PATTERN: Final = re.compile(r"^(?:[0-9a-fA-F]{228}|[0-9a-fA-F]{242})$")

ATTR_PROFILE: Final = "profile"

SERVICE_START: Final = "start"
SERVICE_STOP: Final = "stop"
