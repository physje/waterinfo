"""Sensor for Rijkswaterstaat WaterInfo integration."""

from __future__ import annotations

from datetime import datetime as dt, timedelta
import logging

import ddlpy
import pandas as pd
import pytz

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

from .const import (
    ATTR_LAST_CHECK,
    ATTR_LAST_DATA,
    CONST_COORD,
    CONST_DEVICE_UNIQUE,
    CONST_ENABLE,
    CONST_LAT,
    CONST_LOC_CODE,
    CONST_LOC_NAME,
    CONST_LONG,
    CONST_MEAS_CODE,
    CONST_MEAS_DESCR,
    CONST_MEAS_NAME,
    CONST_PROP,
    CONST_SENSOR,
    CONST_SENSOR_UNIQUE,
    CONST_UNIT,
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
    devices = entry.data[CONST_SENSOR]

    sensors = []
    for device in devices:
        #if device[CONST_PROCES_TYPE] == 'meting':
            device[CONST_DEVICE_UNIQUE] = entry.entry_id
            device[CONST_LOC_CODE] = entry.data[CONST_LOC_CODE]
            sensor = WaterInfoMetingSensor(client, device)
            sensors.append(sensor)

    # Create the sensors.
    async_add_entities(sensors, update_before_add=True)


class WaterInfoMetingSensor(SensorEntity):
    """Defines a Waterinfo sensor."""

    _attr_attribution = "Rijkswaterstaat Waterinfo"
    _attr_has_entity_name = True
    _attr_translation_key = "waterinfo"

    def __init__(self, client: WaterInfoMetingSensor, entry: ConfigEntry) -> None:
        """Initialize a Waterinfo device."""

        # For backwards compatibilty added in version 1.1.0
        self._coord = ""
        self._parameter = ""

        if CONST_COORD in entry:
            self._coord = entry[CONST_COORD]

        if CONST_MEAS_DESCR in entry:
            self._parameter = entry[CONST_MEAS_DESCR]

        if entry[CONST_PROP] not in ['NVT', 'NAP']:
            self._attr_name = entry[CONST_MEAS_NAME]+" "+entry[CONST_PROP]
        else:
            self._attr_name = entry[CONST_MEAS_NAME]

        # Original
        self._id = entry[CONST_LOC_CODE]
        self._X = entry[CONST_LONG]
        self._Y = entry[CONST_LAT]
        self._unit = entry[CONST_UNIT]
        self._grootheid = entry[CONST_MEAS_CODE]
        self._property = entry[CONST_PROP]
        self._name = entry[CONST_LOC_NAME]
        self._attr_unique_id = entry[CONST_DEVICE_UNIQUE] + entry[CONST_SENSOR_UNIQUE]

        self._attr_state_class = SensorStateClass.MEASUREMENT

        if CONST_ENABLE in entry and entry[CONST_ENABLE] == 0:
            self._attr_entity_registry_enabled_default = False

        if entry[CONST_MEAS_CODE] == "T":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_icon = "mdi:water-thermometer"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif entry[CONST_MEAS_CODE] == "WINDSHD":
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:windsock"
            self._attr_device_class = SensorDeviceClass.WIND_SPEED
        elif entry[CONST_MEAS_CODE] == "STROOMSHD":
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:speedometer"
            self._attr_device_class = SensorDeviceClass.SPEED
        elif entry[CONST_MEAS_CODE] == "LUCHTDK":
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:airballoon"
            self._attr_device_class = SensorDeviceClass.PRESSURE
        elif entry[CONST_MEAS_CODE] == "Fp":
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:sine-wave"
            self._attr_device_class = SensorDeviceClass.FREQUENCY
        elif entry[CONST_MEAS_CODE] in ("HTE3", "H1/3", "Hm0", "HEFHTE"):
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:signal-distance-variant"
            self._attr_device_class = SensorDeviceClass.DISTANCE
        elif entry[CONST_MEAS_CODE] == "WATHTE":
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:format-line-height"
            self._attr_device_class = SensorDeviceClass.DISTANCE
        else:
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:water-circle"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry[CONST_DEVICE_UNIQUE]}")},
            manufacturer=entry[CONST_LOC_CODE],
            name=entry[CONST_LOC_NAME],
            entry_type=DeviceEntryType.SERVICE,
        )

        self._last_data = 0
        self._last_check = 0
        self._attrs = {}

    @property
    def extra_state_attributes(self) -> None:
        self._attrs = {
            ATTR_LAST_DATA: self._last_data,
            ATTR_LAST_CHECK: self._last_check
        }
        return self._attrs

    async def async_update(self) -> None:
        """Get the time and updates the states."""

        selected = {
            "Eenheid.Code": self._unit,
            "Grootheid.Code": self._grootheid,
            "Hoedanigheid.Code": self._property,
            "Code": self._id,
            "X": self._X,
            "Y": self._Y,
            "Coordinatenstelsel": self._coord,
            "Naam": self._name,
            "Parameter_Wat_Omschrijving": self._parameter,
        }

        location = pd.Series(selected)

        await self.hass.async_add_executor_job(collectObservation, location)

        # if location["observation"] is not None and location["observation"] != "nan":
        if isinstance(location["observation"], float):
            utc=pytz.UTC

            self._attr_native_value = location["observation"]
            self._last_data = location["tijdstip"]
            self._last_check = dt.now(utc)

            _LOGGER.debug(
                "Observation %s at %s", location["observation"], location["tijdstip"]
            )


def collectObservation(data) -> dict:
    """Collect last measurement for given location/measurement."""

    observation = ddlpy.measurements_latest(data)

    index = len(observation)

    if "Meetwaarde.Waarde_Numeriek" in observation.columns:
        meetwaarde = observation["Meetwaarde.Waarde_Numeriek"].iloc[(index - 1)]
    else:
        meetwaarde = observation["Meetwaarde.Waarde_Alfanumeriek"].iloc[(index - 1)]

    tijdstip_datetime = dt.strptime(
        observation["Tijdstip"].iloc[(index - 1)], "%Y-%m-%dT%H:%M:%S.%f%z"
    )

    data["observation"] = meetwaarde
    data["tijdstip"] = tijdstip_datetime

    return data
