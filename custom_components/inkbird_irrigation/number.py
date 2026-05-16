"""Number platform for Inkbird Irrigation — placeholder for future duration control."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inkbird number entities (none for now)."""
    # Duration control DP not yet discovered.
    # The device uses a fixed 30-minute run time.
    # DP 25-30 are read-only elapsed time counters, not writable duration settings.
    async_add_entities([])
