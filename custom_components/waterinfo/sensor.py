"""Sensor for Rijkswaterstaat WaterInfo integration."""
from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    DOMAIN,
    CONST_CODE,
    CONST_MEASUREMENT_DESCR,
    CONST_MEASUREMENT,
    CONST_UNIT,
    CONST_NAME,
    CONST_X,
    CONST_Y,
    CONST_PROPERTY,
)

import ddlpy2

_LOGGER = logging.getLogger(__name__)

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

        # Code -> _code -> CONST_CODE
        # X -> _X -> CONST_X
        # Y -> _Y -> CONST_Y
        # Eenheid.Code -> _unit -> CONST_UNIT
        # Grootheid.Code -> _grotheid -> CONST_MEASUREMENT
        # Hoedanigheid.Code -> _property -> CONST_PROPERTY
        #
        # Grootheid.Omschrijving -> CONST_MEASUREMENT_DESCR

        self._client = client
        self._code = entry.data[CONST_CODE]
        self._X = entry.data[CONST_X]
        self._Y = entry.data[CONST_Y]
        self._unit = entry.data[CONST_UNIT]
        self._grootheid = entry.data[CONST_MEASUREMENT]
        self._property = entry.data[CONST_PROPERTY]

        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.data[CONST_MEASUREMENT_DESCR]
        self._attr_state_class = SensorStateClass.MEASUREMENT

        if self._grootheid == "T":
            self._attr_native_unit_of_measurement = "°C"
            self._attr_icon = "mdi:water-thermometer"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif self._grootheid == "WINDSHD":
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:windsock"
            self._attr_device_class = SensorDeviceClass.WIND_SPEED
        elif self._grootheid == "STROOMSHD":
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:speedometer"
            self._attr_device_class = SensorDeviceClass.SPEED
        else:
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:water-circle"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}")},
            name=DOMAIN + "_" + entry.data[CONST_NAME],
            entry_type=DeviceEntryType.SERVICE,
        )

        _LOGGER.info(
            "Made sensor for %s (location %s, measurement %s)",
            entry.data[CONST_MEASUREMENT_DESCR],
            entry.data[CONST_CODE],
            entry.data[CONST_MEASUREMENT],
        )

    async def async_update(self) -> None:
        """Get the time and updates the states."""

        # Code -> _code -> CONST_CODE
        # X -> _X -> CONST_X
        # Y -> _Y -> CONST_Y
        # Eenheid.Code -> _unit -> CONST_UNIT
        # Grootheid.Code -> _grootheid -> CONST_MEASUREMENT
        # Hoedanigheid.Code -> _property -> CONST_PROPERTY
        #
        # Grootheid.Omschrijving -> CONST_MEASUREMENT_DESCR

        location = {
            "Eenheid.Code": self._unit,
            "Grootheid.Code": self._grootheid,
            "Hoedanigheid.Code": self._property,
            "Code": self._code,
            "X": self._X,
            "Y": self._Y,
        }

        await self.hass.async_add_executor_job(collectObservation, location)

        if location["observation"] is not None:
            self._attr_native_value = location["observation"]
            _LOGGER.debug(
                "Observation %s at %s", location["observation"], location["tijdstip"]
            )


def collectObservation(data) -> dict:
    observation = ddlpy2.last_observation(data)

    if "Meetwaarde.Waarde_Numeriek" in observation.columns:
        meetwaarde = observation["Meetwaarde.Waarde_Numeriek"][0]
    else:
        meetwaarde = observation["Meetwaarde.Waarde_Alfanumeriek"][0]

    data["observation"] = meetwaarde
    data["tijdstip"] = observation["Tijdstip"][0]

    return data
