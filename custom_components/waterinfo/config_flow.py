"""Config flow for RWS waterinfo integration."""

from __future__ import annotations

from datetime import datetime as dt, timedelta, timezone
import logging
from typing import Any

import ddlpy
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import selector

from .const import (
    CONF_LOC_SELECTOR,
    CONST_COMP_CODE,
    CONST_COORD,
    CONST_ENABLE,
    CONST_GROUP_CODE,
    CONST_LAT,
    CONST_LOC_CODE,
    CONST_LOC_NAME,
    CONST_LONG,
    CONST_MEAS_CODE,
    CONST_MEAS_DESCR,
    CONST_MEAS_NAME,
    CONST_MULTIPLIER,
    CONST_PROCES_TYPE,
    CONST_PROP,
    CONST_SENSOR,
    CONST_SENSOR_UNIQUE,
    CONST_UNIT,
    DEFAULT_TIMEDELTA,
    DOMAIN,
    MIN_TIMEDELTA,
    OPT_TIMEDELTA,
    TIDE_SENSOR_CALCULATED,
    TIDE_SENSOR_FORECAST,
)
from .locations import CONF_LOC_OPTIONS

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    if not await hass.async_add_executor_job(validate_location, data):
        raise InvalidData

    return data
    # return {"title": f"{data[CONST_ID]} - {data[CONST_MEAS]}"}


def validate_location(data) -> dict:
    """Validate the user given location and measurement."""

    locations = ddlpy.locations()
    selected = locations[locations.index == data[CONST_LOC_CODE]]
    if selected.empty:
        _LOGGER.error("Location %s does not exist", data[CONST_LOC_CODE])
        raise ValueError(f"{data[CONST_LOC_CODE]} is geen bestaand station")

    sensoren = []
    seen = []
    disabled = 0

    # Usually, the most recent datapoint are in the last part of the array
    # So walk backwards in the array
    for x in range((len(selected) - 1), -1, -1):
        location = selected.iloc[x]
        code = location.index
        grootheid = location["Grootheid.Code"]
        hoedanigheid = location["Hoedanigheid.Code"]
        groepering = location["Groepering.Code"]
        procestype = location["ProcesType"]

        if hoedanigheid != "NVT":
            sensorKey = grootheid + "_" + hoedanigheid + "_" + procestype
        else:
            sensorKey = grootheid + "_" + procestype

        # If there are tide calculations, update the key as the grootheid and hoedanigheid are the same
        # This is only present for WATHTE astronomisch
        # If this is present we need to retrieve data differently and for two sensors (low/high tide)
        if (
            grootheid == "WATHTE"
            and procestype == "astronomisch"
            and groepering == "GETETBRKD2"
        ):
            sensorKey = TIDE_SENSOR_CALCULATED

        # For the WATHTE verwachting there are no pre-calculated tide points.
        # If verwachting is available we need to calculate it manually, so we add a unique name
        if grootheid == "WATHTE" and procestype == "verwachting":
            sensorKey = TIDE_SENSOR_FORECAST

        # Store all nessecary data for later
        # There are some weird measurements and some measurements are duplicates
        if grootheid != "NVT" and sensorKey not in seen:
            device_info = {}
            device_info[CONST_PROCES_TYPE] = procestype
            device_info[CONST_LOC_CODE] = code
            device_info[CONST_MEAS_CODE] = grootheid
            device_info[CONST_PROP] = hoedanigheid
            device_info[CONST_LOC_NAME] = location["Naam"]
            device_info[CONST_MEAS_NAME] = location["Grootheid.Omschrijving"]
            device_info[CONST_MEAS_DESCR] = location["Parameter_Wat_Omschrijving"]
            device_info[CONST_UNIT] = location["Eenheid.Code"]
            device_info[CONST_LONG] = location["Lon"]
            device_info[CONST_LAT] = location["Lat"]
            device_info[CONST_COMP_CODE] = location["Compartiment.Code"]
            device_info[CONST_COORD] = location["Coordinatenstelsel"]

            if procestype in ("verwachting"):
                device_info[CONST_SENSOR_UNIQUE] = grootheid + "_verwacht"
                device_info[CONST_ENABLE] = 1
            elif procestype in ("astronomisch"):
                device_info[CONST_SENSOR_UNIQUE] = grootheid + "_astronomisch"
                device_info[CONST_ENABLE] = 1
            else:
                device_info[CONST_SENSOR_UNIQUE] = grootheid
                device_info[CONST_ENABLE] = 1

            if hoedanigheid != "NVT":
                device_info[CONST_SENSOR_UNIQUE] = (
                    device_info[CONST_SENSOR_UNIQUE] + "_" + hoedanigheid
                )

            if location["Eenheid.Code"] in ("mHz"):
                device_info[CONST_MULTIPLIER] = 0.001
                device_info[CONST_UNIT] = "Hz"
            else:
                device_info[CONST_MULTIPLIER] = 1

            # If the sensor is set enabled, check if there is recent data
            if device_info[CONST_ENABLE] == 1:
                if procestype in ("meting"):
                    end_date = dt.today()
                    start_date = end_date - timedelta(days=DEFAULT_TIMEDELTA)
                    measurement_available = ddlpy.measurements_available(
                        location, start_date=start_date, end_date=end_date
                    )

                    # if not, disabled
                    if not measurement_available:
                        disabled = disabled + 1
                        device_info[CONST_ENABLE] = 0
                        _LOGGER.info(
                            "Sensor %s is disabled because it has no data",
                            location["Grootheid.Code"],
                        )

            # If it is a GET_WATHTBRKD or GET_WATHTEVERWACHT sensor we need to add two sensors instead
            if sensorKey in (TIDE_SENSOR_CALCULATED, TIDE_SENSOR_FORECAST):
                if groepering not in {"NVT", ""}:
                    device_info[CONST_GROUP_CODE] = groepering

                code_lw = sensorKey + "_LW"
                code_hw = sensorKey + "_HW"

                tide_name_prefix = (
                    "Astronomisch"
                    if sensorKey == TIDE_SENSOR_CALCULATED
                    else "Verwacht"
                )
                tide_description_type = (
                    "astronomische berekeningen"
                    if sensorKey == TIDE_SENSOR_CALCULATED
                    else "weersvoorspellingen"
                )

                device_info_low = device_info.copy()
                device_info_low[CONST_MEAS_NAME] = tide_name_prefix + " Laagwater"
                device_info_low[CONST_MEAS_DESCR] = (
                    "Voorspelt laagwater op basis van " + tide_description_type
                )
                device_info_low[CONST_SENSOR_UNIQUE] = code_lw
                sensoren.append(device_info_low)

                device_info_high = device_info.copy()
                device_info_high[CONST_MEAS_NAME] = tide_name_prefix + " Hoogwater"
                device_info_high[CONST_MEAS_DESCR] = (
                    "Voorspelt hoogwater op basis van " + tide_description_type
                )
                device_info_high[CONST_SENSOR_UNIQUE] = code_hw
                sensoren.append(device_info_high)
            elif len(device_info) > 1:
                sensoren.append(device_info)

            seen.append(sensorKey)

        elif sensorKey in seen:
            _LOGGER.info("Sensor %s (%s) already seen", grootheid, procestype)

    data[CONST_SENSOR] = sensoren
    data[CONST_LOC_NAME] = location["Naam"]

    _LOGGER.info(
        "Made %s sensors for %s (location %s) of which %s are disabled",
        len(sensoren),
        data[CONST_LOC_NAME],
        data[CONST_LOC_CODE],
        disabled,
    )

    return data


class WaterinfoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Rijkswaterstaat WaterInfo."""

    VERSION = 1

    @staticmethod
    # @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        # Remove this method and the ExampleOptionsFlowHandler class
        # if you do not want any options for your integration.
        return WaterInfoFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Check if given codes are valid measurements
                info = await validate_input(self.hass, user_input)
            except ValueError:
                errors["base"] = "invalidData"

            if not errors:
                # Validation was successful, so create a unique id for this instance of your integration
                # and create the config entry.
                await self.async_set_unique_id(info[CONST_LOC_CODE])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info[CONST_LOC_NAME],
                    data=info,
                )

        # Show configflow form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONST_LOC_CODE, default=CONF_LOC_OPTIONS[0]): selector(
                        {
                            "select": {
                                "options": CONF_LOC_OPTIONS,
                                "mode": "dropdown",
                                "translation_key": CONF_LOC_SELECTOR,
                                "sort": True,
                            },
                        }
                    ),
                }
            ),
        )

    # Reconfigure makes usually no sense
    # Reconfigure means a new location, which is new data
    # So instead of reconfigure, just make a new entry
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""
        # This methid displays a reconfigure option in the integration and is
        # different to options.
        # It can be used to reconfigure any of the data submitted when first installed.
        # This is optional and can be removed if you do not want to allow reconfiguration.
        errors: dict[str, str] = {}
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except ValueError:
                errors["base"] = "invalidData"
            else:
                return self.async_update_reload_and_abort(
                    config_entry,
                    unique_id=config_entry.unique_id,
                    data={**config_entry.data, **user_input},
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONST_LOC_CODE, default=config_entry.unique_id
                    ): selector(
                        {
                            "select": {
                                "options": CONF_LOC_OPTIONS,
                                "mode": "dropdown",
                                "translation_key": CONF_LOC_SELECTOR,
                            },
                        }
                    ),
                }
            ),
            errors=errors,
        )


class WaterInfoFlowHandler(OptionsFlow):
    """Handles the options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            options = self.config_entry.options | user_input
            return self.async_create_entry(title="", data=options)

        # It is recommended to prepopulate options fields with default values if available.
        # These will be the same default values you use on your coordinator for setting variable values
        # if the option has not been set.
        data_schema = vol.Schema(
            {
                vol.Required(
                    OPT_TIMEDELTA,
                    default=self.options.get(OPT_TIMEDELTA, DEFAULT_TIMEDELTA),
                ): (vol.All(vol.Coerce(int), vol.Clamp(min=MIN_TIMEDELTA))),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


class InvalidData(HomeAssistantError):
    """Error to indicate there is invalid auth."""
