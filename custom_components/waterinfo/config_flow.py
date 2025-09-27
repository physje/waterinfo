"""Config flow for RWS waterinfo integration."""

from __future__ import annotations

from datetime import datetime as dt, timedelta
import logging
import random
import string
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
    CONST_COORD,
    CONST_ENABLE,
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

    x_coord_len = 100
    x_coord_short = ""

    # Usually, the most recent datapoint are in the last part of the array
    # So walk backwards in the array
    for x in range((len(selected) - 1), -1, -1):
        X_coord = selected.iloc[x]["X"]

        # Somewhere around Sept. 9th, the duplicates all locations.
        # The only difference is the precision of the X- and Y-coordinate
        # So quick-and-dirty find of the shortest X-coordinate
        if len(str(X_coord)) < x_coord_len:
            x_coord_short = X_coord
            x_coord_len = len(str(X_coord))

    sensoren = []
    seen = []

    # Usually, the most recent datapoint are in the last part of the array
    # So walk backwards in the array
    for x in range((len(selected) - 1), -1, -1):
        grootheid = selected.iloc[x]["Grootheid.Code"]
        hoedanigheid = selected.iloc[x]["Hoedanigheid.Code"]
        X_coord = selected.iloc[x]["X"]

        if hoedanigheid != "NVT":
            sensorKey = grootheid + hoedanigheid
        else:
            sensorKey = grootheid

        # Store all nessecary data for later
        # There are some weird measurements and some measurements are duplicates
        if grootheid != "NVT" and sensorKey not in seen and X_coord == x_coord_short:
            device_info = {}
            device_info[CONST_LOC_NAME] = selected.iloc[x]["Naam"]
            device_info[CONST_MEAS_CODE] = grootheid
            device_info[CONST_MEAS_NAME] = selected.iloc[x]["Grootheid.Omschrijving"]
            device_info[CONST_MEAS_DESCR] = selected.iloc[x][
                "Parameter_Wat_Omschrijving"
            ]
            device_info[CONST_UNIT] = selected.iloc[x]["Eenheid.Code"]
            device_info[CONST_LONG] = selected.iloc[x]["X"]
            device_info[CONST_LAT] = selected.iloc[x]["Y"]
            device_info[CONST_PROP] = hoedanigheid
            device_info[CONST_COORD] = selected.iloc[x]["Coordinatenstelsel"]

            device_info[CONST_SENSOR_UNIQUE] = grootheid

            if selected.iloc[x]["Eenheid.Code"] in ("mHz"):
                device_info[CONST_MULTIPLIER] = 0.001
                device_info[CONST_UNIT] = "Hz"
            else:
                device_info[CONST_MULTIPLIER] = 1

            if grootheid in ("WATHTBRKD", "WATHTEASTRO"):
                device_info[CONST_PROCES_TYPE] = "astronomisch"
                device_info[CONST_ENABLE] = 0
            elif grootheid in ("WATHTEVERWACHT", "QVERWACHT"):
                device_info[CONST_PROCES_TYPE] = "verwacht"
                device_info[CONST_ENABLE] = 0
            else:
                device_info[CONST_PROCES_TYPE] = "meting"
                device_info[CONST_ENABLE] = 1

            # If the sensor is set enabled, check if there is recent data
            if device_info[CONST_ENABLE] == 1:
                end_date = dt.today()
                start_date = end_date - timedelta(days=14)
                measurements = ddlpy.measurements(
                    selected.iloc[x], start_date=start_date, end_date=end_date
                )

                # if not, disabled
                if measurements.empty:
                    device_info[CONST_ENABLE] = 0

            seen.append(sensorKey)
            sensoren.append(device_info)

    data[CONST_SENSOR] = sensoren
    data[CONST_LOC_NAME] = selected.iloc[x]["Naam"]

    _LOGGER.info(
        "Made %s sensors for %s (location %s)",
        len(seen),
        data[CONST_LOC_NAME],
        data[CONST_LOC_CODE],
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

    # Reconfigure makes no sense
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
