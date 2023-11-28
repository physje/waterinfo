"""Sensor for Rijkswaterstaat WaterInfo integration."""
from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    DOMAIN,
    CONST_CODE,
    CONST_STATION,
    CONST_MEASUREMENT,
    CONST_UNIT,
    CONST_NAME,
    CONST_X,
    CONST_Y,
    CONST_PROPERTY,
)

import ddlpy2
import urllib.parse

# Time between updating data from Webservice
SCAN_INTERVAL = timedelta(minutes=10)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Waterinfo sensor from a config entry."""
    client = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WaterInfoSensor(client, entry)], update_before_add=True)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Create the sensor."""
    sensors = []
    sensors.append(WaterInfoSensor(config))

    async_add_entities(sensors, True)


class WaterInfoSensor(SensorEntity):
    """Defines a Waterinfo sensor."""

    _attr_attribution = "Rijkswaterstaat Waterinfo"
    _attr_has_entity_name = True
    _attr_translation_key = "waterinfo"

    def __init__(self, client: Waterinfo, entry: ConfigEntry) -> None:
        """Initialize a Waterinfo device."""

        self._client = client
        # self._location = entry.data[CONST_LOCATION]
        self._station = entry.data[CONST_STATION]
        self._X = entry.data[CONST_X]
        self._Y = entry.data[CONST_Y]
        self._unit = entry.data[CONST_UNIT]
        self._code = entry.data[CONST_CODE]
        self._property = entry.data[CONST_PROPERTY]
        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.data[CONST_MEASUREMENT]
        # native_value
        self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
        self._attr_icon = "mdi:water-circle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}")},
            name=entry.data[CONST_NAME],
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_update(self) -> None:
        """Get the time and updates the states."""

        # print("async_update")
        # print(location)

        # location = urllib.parse.parse_qsl(self._location)
        # observation = ddlpy2.last_observation(location)

        # Code -> CONST_STATION
        # X -> CONST_X
        # Y -> CONST_Y
        # Eenheid.Code -> CONST_UNIT
        # Grootheid.Code -> CONST_CODE
        # Hoedanigheid.Code -> CONST_PROPERTY

        location = {
            "Code": self._station,
            "X": self._X,
            "Y": self._Y,
            "Eenheid.Code": self._unit,
            "Grootheid.Code": self._code,
            "Hoedanigheid.Code": self._property,
        }

        await self.hass.async_add_executor_job(collectObservation, location)

        if location["observation"] == None:
            self._attr_native_value = 1
        else:
            self._attr_native_value = location["observation"]


def collectObservation(data) -> dict:
    observation = ddlpy2.last_observation(data)
    meetwaarde = observation["Meetwaarde.Waarde_Numeriek"][0]

    data["observation"] = meetwaarde

    return data
