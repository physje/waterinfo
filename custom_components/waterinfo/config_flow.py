"""Config flow for RWS waterinfo integration."""

from __future__ import annotations

import logging
from typing import Any

import ddlpy
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (CONST_CODE, CONST_MEASUREMENT, CONST_MEASUREMENT_DESCR,
                    CONST_NAME, CONST_PROPERTY, CONST_UNIT, CONST_X, CONST_Y,
                    DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    if not await hass.async_add_executor_job(validate_location, data):
        raise InvalidAuth

    return data


def validate_location(data) -> dict:
    """Validate the user given location and measurement."""

    locations = ddlpy.locations()
    selected = locations[locations.index == data[CONST_CODE]]
    if selected.empty:
        _LOGGER.error("Location %s does not exist", data[CONST_CODE])
        raise ValueError(f"{data[CONST_CODE]} is geen bestaand station")

    selected = selected[
        (selected["Grootheid.Code"] == data[CONST_MEASUREMENT])
    ].reset_index()
    if selected.empty:
        _LOGGER.error(
            "Measurements %s does not exist for %s",
            data[CONST_MEASUREMENT],
            data[CONST_CODE],
        )
        raise ValueError(f"{data[CONST_MEASUREMENT]} is geen bestaande meetwaarde")

    selected_location = selected.loc[0]

    data[CONST_MEASUREMENT_DESCR] = selected_location["Grootheid.Omschrijving"]
    data[CONST_NAME] = selected_location["Naam"]
    data[CONST_UNIT] = selected_location["Eenheid.Code"]
    data[CONST_X] = selected_location["X"]
    data[CONST_Y] = selected_location["Y"]
    data[CONST_PROPERTY] = selected_location["Hoedanigheid.Code"]

    # data[] = selected_location["Coordinatenstelsel"]
    # data[] = selected_location["Naam"]
    # data[] = selected_location["Parameter_Wat_Omschrijving"]

    # Code -> CONST_CODE
    # X -> CONST_X
    # Y -> CONST_Y
    # Eenheid.Code -> CONST_UNIT
    # Grootheid.Code -> CONST_MEASUREMENT
    # Grootheid.Omschrijving -> CONST_MEASUREMENT_DESCR
    # Hoedanigheid.Code -> CONST_PROPERTY

    _LOGGER.info(
        "Made sensor for %s (location %s, measurement %s)",
        data[CONST_MEASUREMENT_DESCR],
        data[CONST_CODE],
        data[CONST_MEASUREMENT],
    )

    return data


class WaterinfoFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Rijkswaterstaat WaterInfo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except ValueError:
                errors["base"] = "auth"
            if not errors:
                # self.data = user_input
                return self.async_create_entry(
                    title=info["plaats"],
                    data=info,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONST_CODE): str,
                    vol.Required(CONST_MEASUREMENT): str,
                }
            ),
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
