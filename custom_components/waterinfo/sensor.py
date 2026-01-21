"""Sensor for Rijkswaterstaat WaterInfo integration."""

from __future__ import annotations

from datetime import datetime as dt, timedelta, timezone
import logging

import ddlpy
import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy.signal import find_peaks, savgol_filter

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
    ATTR_EXPECTED_TIME,
    ATTR_LAST_CHECK,
    ATTR_LAST_DATA,
    CONST_COMP_CODE,
    CONST_COORD,
    CONST_DEVICE_UNIQUE,
    CONST_ENABLE,
    CONST_GROUP_CODE,
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
    TIDE_SENSOR_CALCULATED,
    TIDE_SENSOR_FORECAST,
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

        if entry[CONST_PROCES_TYPE] == "astronomisch":
            self._attr_name = self._attr_name + " (astronomisch)"

        # self._attr_name = self._attr_name + entry[CONST_GROUP_CODE]

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
        self._sensor_unique = entry[CONST_SENSOR_UNIQUE]

        self._groepering = None
        if CONST_GROUP_CODE in entry:
            self._groepering = entry[CONST_GROUP_CODE]

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
        elif (
            entry[CONST_SENSOR_UNIQUE] == TIDE_SENSOR_CALCULATED + "_LW"
            or entry[CONST_SENSOR_UNIQUE] == TIDE_SENSOR_FORECAST + "_LW"
        ):
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:wave-arrow-down"
            self._attr_device_class = SensorDeviceClass.DISTANCE
        elif (
            entry[CONST_SENSOR_UNIQUE] == TIDE_SENSOR_CALCULATED + "_HW"
            or entry[CONST_SENSOR_UNIQUE] == TIDE_SENSOR_FORECAST + "_HW"
        ):
            self._attr_native_unit_of_measurement = entry[CONST_UNIT]
            self._attr_icon = "mdi:wave-arrow-up"
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
        self._expec_time = 0
        self._attrs = {}

    @property
    def extra_state_attributes(self) -> None:
        """Add extra attributes with time of last data and time of last check."""

        if self._procestype == "meting":
            self._attrs = {
                ATTR_LAST_DATA: self._last_data,
                ATTR_LAST_CHECK: self._last_check,
            }
        else:
            self._attrs = {
                ATTR_EXPECTED_TIME: self._expec_time,
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

        if self._sensor_unique.startswith(TIDE_SENSOR_CALCULATED):
            if (self._groepering is not None) and (self._groepering != ""):
                location["Groepering.Code"] = self._groepering

            if (self._procestype is not None) and (self._procestype != ""):
                location["ProcesType"] = self._procestype

            await self.hass.async_add_executor_job(
                collectCalculatedTideObservation,
                location,
                self._sensor_unique.endswith("_LW"),
            )
        elif self._sensor_unique.startswith(TIDE_SENSOR_FORECAST):
            if (self._procestype is not None) and (self._procestype != ""):
                location["ProcesType"] = self._procestype

            await self.hass.async_add_executor_job(
                collectForecastTideObservation,
                location,
                self._sensor_unique.endswith("_LW"),
            )
        else:
            await self.hass.async_add_executor_job(collectObservation, location)

        # if location["observation"] is not None and location["observation"] != "nan":
        if isinstance(location["observation"], float):
            self._attr_native_value = location["observation"]
            self._last_check = dt.now(timezone.utc)

            if self._procestype == "meting":
                self._last_data = location["tijdstip"]
            else:
                self._expec_time = location["tijdstip"]

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

        _LOGGER.debug(
            "No observations for %s at %s", data["Grootheid.Code"], data["Naam"]
        )

    return data


def collectCalculatedTideObservation(data, is_low_tide: bool) -> dict:
    """Collect last calculated tide measurement for a given location (astronomical via GETETBRKD2)."""
    try:
        # According to documentation we need to start from 10 minutes ago until at most 2 days in the future
        # One day should be enough to get the next low and high tide
        observations = ddlpy.measurements(
            data,
            start_date=dt.now(tz=timezone.utc) - timedelta(minutes=10),
            end_date=dt.now(tz=timezone.utc) + timedelta(days=1),
        )
        observations = ddlpy.simplify_dataframe(observations)

        first_two = observations.head(2)
        if is_low_tide:
            idx = int(first_two["Meetwaarde.Waarde_Numeriek"].argmin())
        else:
            idx = int(first_two["Meetwaarde.Waarde_Numeriek"].argmax())

        data["observation"] = observations["Meetwaarde.Waarde_Numeriek"].iloc[idx]
        data["tijdstip"] = observations.index[idx].to_pydatetime()
    except Exception:
        data["observation"] = None
        data["tijdstip"] = None

        _LOGGER.error(
            "No calculated data for %s at %s", TIDE_SENSOR_CALCULATED, data["Naam"]
        )

    return data


def collectForecastTideObservation(data, is_low_tide: bool) -> dict:
    """Collect the next forecasted tides for a given location (calculated on the forecasted datapoints)."""
    try:
        # To make sure we can catch an ongoing tide we start 6 hours back and go 1 day forward
        observations = ddlpy.measurements(
            data,
            start_date=dt.now() - timedelta(hours=6),
            end_date=dt.now() + timedelta(days=1),
        )
        observations = ddlpy.simplify_dataframe(observations)

        if (
            observations.empty
            or "Meetwaarde.Waarde_Numeriek" not in observations.columns
        ):
            raise ValueError("No observation data available")

        values = observations["Meetwaarde.Waarde_Numeriek"].to_numpy()

        # Savitzky-Golay filter parameters:
        # window_length: must be odd, ~1-2 hours of data points
        # polyorder: polynomial order (3 works well for tidal curves)
        window_length = min(
            13, len(values) if len(values) % 2 == 1 else len(values) - 1
        )
        if window_length < 5:
            raise ValueError("Not enough data points for smoothing")

        smoothed: np.ndarray = savgol_filter(
            values, window_length=window_length, polyorder=3
        )

        peak_params = {
            "distance": 24,  # 4 hours minimum between extremes
            "prominence": 10,  # 10 cm minimum prominence
            "width": 3,  # peak must span at least 3 points
        }

        if is_low_tide:
            # Find troughs by inverting the signal
            indices, _ = find_peaks(-smoothed, **peak_params)
        else:
            indices, _ = find_peaks(smoothed, **peak_params)

        if len(indices) == 0:
            raise ValueError("No tide extremes found")

        # make sure the found peak is at a time larger or equal than the current time (accounting for timezones)
        current_time = dt.now(timezone.utc)
        indices = [i for i in indices if observations.index[i] >= current_time]

        idx = int(indices[0])
        data["observation"] = observations["Meetwaarde.Waarde_Numeriek"].iloc[idx]
        data["tijdstip"] = observations.index[idx].to_pydatetime()

    except Exception:
        data["observation"] = None
        data["tijdstip"] = None
        _LOGGER.error("No forecast for %s at %s", TIDE_SENSOR_FORECAST, data["Naam"])

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
