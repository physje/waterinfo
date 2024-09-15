"""Sensor for Rijkswaterstaat WaterInfo integration."""

from __future__ import annotations

from datetime import datetime as dt, timedelta
import logging

import ddlpy
import pandas as pd

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    ATRR_MEASUREMENT,
    ATTR_DESCR,
    ATTR_LAST_DATA,
    ATTR_LOCATION,
    CONST_CODE,
    CONST_COORD,
    CONST_MEASUREMENT,
    CONST_MEASUREMENT_DESCR,
    CONST_NAME,
    CONST_PAREMETER_DESCR,
    CONST_PROPERTY,
    CONST_UNIT,
    CONST_X,
    CONST_Y,
    DOMAIN,
)

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

    def __init__(self, client: WaterInfoSensor, entry: ConfigEntry) -> None:
        """Initialize a Waterinfo device."""

        # For backwards compatibilty added in version 1.1.0
        self._coord = ""
        self._parameter = ""

        if CONST_COORD in entry.data:
            self._coord = entry.data[CONST_COORD]

        if CONST_PAREMETER_DESCR in entry.data:
            self._parameter = entry.data[CONST_PAREMETER_DESCR]

        # Original
        self._code = entry.data[CONST_CODE]
        self._X = entry.data[CONST_X]
        self._Y = entry.data[CONST_Y]
        self._unit = entry.data[CONST_UNIT]
        self._grootheid = entry.data[CONST_MEASUREMENT]
        self._property = entry.data[CONST_PROPERTY]
        self._name = entry.data[CONST_NAME]
        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.data[CONST_MEASUREMENT_DESCR]
        self._attr_state_class = SensorStateClass.MEASUREMENT

        if entry.data[CONST_MEASUREMENT] == "T":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_icon = "mdi:water-thermometer"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif entry.data[CONST_MEASUREMENT] == "WINDSHD":
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:windsock"
            self._attr_device_class = SensorDeviceClass.WIND_SPEED
        elif entry.data[CONST_MEASUREMENT] == "STROOMSHD":
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:speedometer"
            self._attr_device_class = SensorDeviceClass.SPEED
        elif entry.data[CONST_MEASUREMENT] == "LUCHTDK":
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:airballoon"
            self._attr_device_class = SensorDeviceClass.PRESSURE
        elif entry.data[CONST_MEASUREMENT] == "Fp":
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:sine-wave"
            self._attr_device_class = SensorDeviceClass.FREQUENCY
        elif entry.data[CONST_MEASUREMENT] in ("HTE3", "H1/3", "Hm0", "HEFHTE"):
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:signal-distance-variant"
            self._attr_device_class = SensorDeviceClass.DISTANCE
        else:
            self._attr_native_unit_of_measurement = entry.data[CONST_UNIT]
            self._attr_icon = "mdi:water-circle"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}")},
            name=entry.data[CONST_NAME],
            entry_type=DeviceEntryType.SERVICE,
        )

        self._last_data = 0
        self._attrs = {}



    @property
    def extra_state_attributes(self) -> None:
        self._attrs = {
            ATTR_LAST_DATA: self._last_data,
            ATRR_MEASUREMENT: self._attr_name +" ["+ self._grootheid +"]",
            ATTR_LOCATION: self._name +" ["+ self._code +"]",
            #ATTR_X: self._X,
            #ATTR_Y: self._Y,
            ATTR_DESCR: self._parameter,
        }
        return self._attrs



    async def async_update(self) -> None:
        """Get the time and updates the states."""

        selected = {
            "Eenheid.Code": self._unit,
            "Grootheid.Code": self._grootheid,
            "Hoedanigheid.Code": self._property,
            "Code": self._code,
            "X": self._X,
            "Y": self._Y,
            "Coordinatenstelsel": self._coord,
            "Naam": self._name,
            "Parameter_Wat_Omschrijving": self._parameter,
        }

        location = pd.Series(selected)

        await self.hass.async_add_executor_job(collectObservation, location)

        if location["observation"] is not None:
            self._attr_native_value = location["observation"]
            self._last_data = location["tijdstip"]

            _LOGGER.debug(
                "Observation %s at %s", location["observation"], location["tijdstip"]
            )



def collectObservation(data) -> dict:
    """Collect last measurement for given location/measurement."""

    observation = ddlpy.measurements_latest(data)

    if "Meetwaarde.Waarde_Numeriek" in observation.columns:
        meetwaarde = observation["Meetwaarde.Waarde_Numeriek"].iloc[0]
    else:
        meetwaarde = observation["Meetwaarde.Waarde_Alfanumeriek"].iloc[0]

    tijdstip_datetime = dt.strptime(observation["Tijdstip"].iloc[0], '%Y-%m-%dT%H:%M:%S.%f%z')

    data["observation"] = meetwaarde
    data["tijdstip"] = tijdstip_datetime

    return data
