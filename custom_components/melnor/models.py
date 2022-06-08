"""melnor integration models."""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from melnor_bluetooth.device import Device

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MelnorDataUpdateCoordinator(DataUpdateCoordinator[Device]):
    """Melnor data update coordinator."""

    _device: Device
    _has_active_connection: bool = False

    def __init__(self, hass: HomeAssistant, device: Device) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Melnor Bluetooth",
            update_interval=timedelta(seconds=5),
        )
        self._device = device

    async def _async_update_data(self):
        """Update data."""

        if self._device.is_connected:

            if not self._has_active_connection:
                _LOGGER.debug("%s has re-connected", self._device.mac)

            self._has_active_connection = True
            await self._device.fetch_state()

        # The melnor-bluetooth library handles exceptions for us.
        # We just need to check the connection state and attempt to self-heal the connection if it drops.
        else:

            if self._has_active_connection:
                self._has_active_connection = False
                _LOGGER.warning("%s has disconnected", self._device.mac)

                # Since we just became disconnected we'll return early to trigger an entity update ASAP to show the entities as unavailable.
                # We update frequently and we'll start attempting to reconnect on the next pass in a few seconds.
                return self._device

            await self._device.connect(timeout=10)

        return self._device


class MelnorBluetoothBaseEntity(CoordinatorEntity[MelnorDataUpdateCoordinator]):
    """Base class for melnor entities."""

    _device: Device

    def __init__(
        self,
        coordinator: MelnorDataUpdateCoordinator,
    ) -> None:
        """Initialize a melnor base entity."""
        super().__init__(coordinator)

        self._device = coordinator.data

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._device = self.coordinator.data
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._device.is_connected

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._device.name

    @property
    def unique_id(self) -> str:
        """Return a base unique ID."""
        return f"{self._device.mac}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.mac)},
            manufacturer="Melnor",
            model=self._device.model,
            name=self._device.name,
        )
