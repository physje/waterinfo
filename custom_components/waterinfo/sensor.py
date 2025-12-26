"""Sensor for Rijkswaterstaat WaterInfo integration."""

from __future__ import annotations

from datetime import datetime as dt, timedelta, timezone
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

from .const import (
    ATTR_LAST_CHECK,
    ATTR_LAST_DATA,
    CONST_COMP_CODE,
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
        # if device[CONST_PROCES_TYPE] == 'meting':
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

        if entry[CONST_PROP] not in ["NVT", "NAP"]:
            self._attr_name = entry[CONST_MEAS_NAME] + " " + entry[CONST_PROP]
        else:
            self._attr_name = entry[CONST_MEAS_NAME]

        # Original
        self._id = entry[CONST_LOC_CODE]
        self._long = entry[CONST_LONG]
        self._lat = entry[CONST_LAT]
        self._unit = entry[CONST_UNIT]
        self._grootheid = entry[CONST_MEAS_CODE]
        self._property = entry[CONST_PROP]
        self._name = entry[CONST_LOC_NAME]
        self._comp_code = entry[CONST_COMP_CODE]
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
        """Add extra attributes with time of last data and time of last check."""
        self._attrs = {
            ATTR_LAST_DATA: self._last_data,
            ATTR_LAST_CHECK: self._last_check,
        }
        return self._attrs

    async def async_update(self) -> None:
        """Get the time and updates the states."""

        selected = {
            "Compartiment.Code": self._comp_code,
            "Grootheid.Code": self._grootheid,
            "Code": self._id,
            "Lat": self._lat,
            "Lon": self._long,
            "Coordinatenstelsel": self._coord,
            "Naam": self._name,
        }

        location = pd.Series(selected)

        await self.hass.async_add_executor_job(collectObservation, location)

        # if location["observation"] is not None and location["observation"] != "nan":
        if isinstance(location["observation"], float):
            self._attr_native_value = location["observation"]
            self._last_data = location["tijdstip"]
            self._last_check = dt.now(timezone.utc)

            _LOGGER.debug(
                "Observation %s at %s", location["observation"], location["tijdstip"]
            )


def collectObservation(data) -> dict:
    """Collect last measurement for given location/measurement."""

    try:
        observation = ddlpy.measurements_latest(data)

        # t is list of all observation times, m is a list of all measurements
        t = []
        m = []

        # walk through all measurements
        for y in range(len(observation)):
            if "Meetwaarde.Waarde_Numeriek" in observation.columns:
                meetwaarde = observation["Meetwaarde.Waarde_Numeriek"].iloc[y]
            else:
                meetwaarde = observation["Meetwaarde.Waarde_Alfanumeriek"].iloc[y]

            tijdstip = observation["Tijdstip"].iloc[y]

            t.append(tijdstip)
            m.append(meetwaarde)

        # find the index of the latest observation
        # this measurement will be returned
        max_t = max(t)
        index_t = t.index(max_t)

        tijdstip_datetime = dt.strptime(t[index_t], "%Y-%m-%dT%H:%M:%S.%f%z")

        data["observation"] = m[index_t]
        data["tijdstip"] = tijdstip_datetime
    except:
        data["observation"] = None
        data["tijdstip"] = None

        _LOGGER.error("No data for %s at %s", data["Grootheid.Code"], data["Naam"])

    return data
