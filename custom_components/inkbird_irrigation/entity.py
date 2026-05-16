"""Base entity for Inkbird Irrigation."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import InkbirdCoordinator


class InkbirdEntity(CoordinatorEntity[InkbirdCoordinator]):
    """Base class for Inkbird entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: InkbirdCoordinator) -> None:
        super().__init__(coordinator)
        self._device_id = coordinator.entry.data["device_id"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self.coordinator.entry.data.get("device_name", "Inkbird IIC-600"),
            manufacturer="Inkbird",
            model="IIC-600-WIFI",
        )
