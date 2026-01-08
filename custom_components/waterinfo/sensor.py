"""Sensor for Rijkswaterstaat WaterInfo integration."""

from __future__ import annotations

import logging

import ddlpy
import pandas as pd

import numpy as np
import numpy.typing as npt
from scipy.signal import find_peaks

from datetime import datetime as dt
from datetime import timedelta, timezone

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
    ATTR_PREDICT_TIME,
    CONST_COMP_CODE,
    CONST_COORD,
    CONST_DEVICE_UNIQUE,
    CONST_ENABLE,
    CONST_EXPEC_TYPE,
    CONST_LAT,
    CONST_LOC_CODE,
    CONST_LOC_NAME,
    CONST_LONG,
    CONST_MEAS_CODE,
    CONST_MEAS_DESCR,
    CONST_MEAS_NAME,
    CONST_PROCES_TYPE,
    CONST_PROP,
    CONST_SENSOR,
    CONST_SENSOR_UNIQUE,
    CONST_UNIT,
    DOMAIN,
    PEAK_DISTANCE,
    PEAK_PROMINENCE,
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

        if entry[CONST_PROCES_TYPE] == "verwachting":
            self._attr_name = self._attr_name + " (verwachting)"

        if CONST_EXPEC_TYPE in entry:
            self._expectation_type = entry[CONST_EXPEC_TYPE]
        else:
            self._expectation_type = "meting"

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
        self._procestype = entry[CONST_PROCES_TYPE]

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
            self._attr_device_class = SensorDeviceClass.DISTANCE

            """
            if entry[CONST_PROCES_TYPE] == "verwachting":
                if entry[CONST_EXPEC_TYPE] == "max":
                    self._attr_icon = "mdi:wave-arrow-up"
                elif entry[CONST_EXPEC_TYPE] == "min":
                    self._attr_icon = "mdi:wave-arrow-down"
            else:
                self._attr_icon = "mdi:format-line-height"
            """
        else:
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:water-circle"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry[CONST_DEVICE_UNIQUE]}")},
            manufacturer=entry[CONST_LOC_CODE],
            name=entry[CONST_LOC_NAME],
            entry_type=DeviceEntryType.SERVICE,
        )

        if self._expectation_type == "verwachting":
            self._predict_time = 0
        else:
            self._last_data = 0

        self._last_check = 0
        self._attrs = {}

    @property
    def extra_state_attributes(self) -> None:
        """Add extra attributes with time of last data and time of last check."""

        if self._expectation_type == "verwachting":
            self._attrs = {
                ATTR_LAST_CHECK: self._last_check,
                ATTR_PREDICT_TIME: self._predict_time,
            }
        else:
            self._attrs = {
                ATTR_LAST_CHECK: self._last_check,
                ATTR_LAST_DATA: self._last_data,
            }

        return self._attrs

    async def async_update(self) -> None:
        """Get the time and updates the states."""

        if self._procestype == "verwachting":
            selected = {
                "Compartiment.Code": self._comp_code,
                "Grootheid.Code": self._grootheid,
                "Code": self._id,
                "Lat": self._lat,
                "Lon": self._long,
                "Coordinatenstelsel": self._coord,
                "Naam": self._name,
                "ProcesType": self._procestype,
            }

            location = pd.Series(selected)

            await self.hass.async_add_executor_job(
                collectExpectation, location, self._expectation_type
            )

            # if location["observation"] is not None and location["observation"] != "nan":
            if isinstance(location["expectation"], float):
                self._attr_native_value = location["expectation"]
                self._predict_time = location["tijdstip"]
                self._last_check = dt.now(timezone.utc)

                _LOGGER.debug(
                    "Prediction %s at %s",
                    location["expectation"],
                    location["tijdstip"],
                )
        else:
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
                    "Observation %s at %s",
                    location["observation"],
                    location["tijdstip"],
                )


def collectObservation(data) -> dict:
    """Collect last measurement for given location/measurement."""

    try:
        observation = ddlpy.measurements_latest(data)

        records = []
        for index, row in observation.iterrows():
            timestamp = pd.to_datetime(row.get("Tijdstip")).tz_convert("UTC")
            waarde = row.get("Meetwaarde.Waarde_Numeriek")

            if waarde is not None:
                records.append({"Tijdstip": timestamp, "Waarde": waarde})

        df = pd.DataFrame(records)
        df.set_index("Tijdstip", inplace=True)
        df = df.sort_index(ascending=False)

        data["observation"] = df.head(1)["Waarde"].to_numpy()[0]
        data["tijdstip"] = df.head(1).index.to_numpy()[0]
    except:
        data["observation"] = None
        data["tijdstip"] = None

        _LOGGER.debug("No data for %s at %s", data["Grootheid.Code"], data["Naam"])

    return data


def collectExpectation(data, type) -> dict:
    """Collect expected values for given location/measurement."""

    try:
        start_date = dt.today() - timedelta(hours=1)
        end_date = start_date + timedelta(days=7)

        ddlpy_data = ddlpy.measurements(data, start_date=start_date, end_date=end_date)

        records = []
        for index, row in ddlpy_data.iterrows():
            timestamp = pd.to_datetime(index).tz_convert("UTC")
            waarde = row.get("Meetwaarde.Waarde_Numeriek")

            if waarde is not None:
                records.append({"Tijdstip": timestamp, "Waarde": waarde})

            df = pd.DataFrame(records)
            df.set_index("Tijdstip", inplace=True)

        data["expectation"] = None
        data["tijdstip"] = None

        _LOGGER.debug(
            "%s predicted elements for %s at %s",
            len(df),
            data["Grootheid.Code"],
            data["Naam"],
        )

        if data["Grootheid.Code"] == "WATHTE":
            high_tides, low_tides = find_tide_extremes(df)

            if not high_tides.empty or not low_tides.empty:
                if type == "max":
                    tide = high_tides.head(1)
                elif type == "min":
                    tide = low_tides.head(1)

                data["expectation"] = tide["Waarde"].to_numpy()[0]
                data["tijdstip"] = tide.index.to_numpy()[0]
            else:
                if type == "max":
                    data["expectation"] = max(df["Waarde"]).to_numpy()[0]
                elif type == "min":
                    data["expectation"] = min(df["Waarde"]).to_numpy()[0]

                data["tijdstip"] = (
                    df.where(df["Waarde"] == data["expectation"])
                    .dropna()
                    .index.to_numpy()[0]
                )

    except:
        data["expectation"] = None
        data["tijdstip"] = None

        _LOGGER.debug("No data for %s at %s", data["Grootheid.Code"], data["Naam"])

    return data


def find_tide_extremes(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    @leondeklerk
    https://github.com/leondeklerk/waterinfo

    Find tide extremes using scipy.signal.find_peaks.

    Args:
        df: DataFrame with 'Waarde' column containing water level predictions and datetime index

    Returns:
        Tuple of (high_tides, low_tides) DataFrames
    """
    if df.empty or "Waarde" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    values: npt.NDArray[np.float64] = df["Waarde"].to_numpy()

    # Find peaks (high tides)
    high_indices, _ = find_peaks(
        values, distance=PEAK_DISTANCE, prominence=PEAK_PROMINENCE
    )

    # Find troughs (low tides) by inverting the signal
    low_indices, _ = find_peaks(
        -values, distance=PEAK_DISTANCE, prominence=PEAK_PROMINENCE
    )

    high_tides = df.iloc[high_indices]
    low_tides = df.iloc[low_indices]

    return high_tides, low_tides
