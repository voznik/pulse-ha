"""Constants for the Pulse integration."""

from .helpers import VERDICTS

DOMAIN = "pulse_monitor"
CONF_API_TOKEN = "api_token"
SCAN_INTERVAL_SECONDS = 30

__all__ = ["CONF_API_TOKEN", "DOMAIN", "SCAN_INTERVAL_SECONDS", "VERDICTS"]
