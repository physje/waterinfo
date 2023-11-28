"""Config flow for RWS waterinfo integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import ConfigFlow
from homeassistant.exceptions import HomeAssistantError

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

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    # your_validate_func, data["username"], data["password"]
    #    locations = ddlpy2.locations()
    #
    #       selected = locations[locations.index == data["station"]]
    #
    #       selected = selected[(selected["Grootheid.Code"] == data["code"])].reset_index()
    #
    #       data["location"] = selected.loc[0]
    #  )

    await hass.async_add_executor_job(validate_location, data)

    return data

    # if not await hub.authenticate(data["username"], data["password"]):
    #    raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    # return data


def validate_location(data) -> dict:
    locations = ddlpy2.locations()
    selected = locations[locations.index == data[CONST_STATION]]
    selected = selected[(selected["Grootheid.Code"] == data[CONST_CODE])].reset_index()

    selected_location = selected.loc[0]

    # data[CONST_LOCATION] = urllib.parse.urlencode()
    data[CONST_MEASUREMENT] = selected_location["Grootheid.Omschrijving"]
    data[CONST_NAME] = selected_location["Naam"]
    data[CONST_UNIT] = selected_location["Eenheid.Code"]
    data[CONST_X] = selected_location["X"]
    data[CONST_Y] = selected_location["Y"]
    data[CONST_PROPERTY] = selected_location["Hoedanigheid.Code"]

    # Code -> CONST_STATION
    # X -> CONST_X
    # Y -> CONST_Y
    # Eenheid.Code -> CONST_UNIT
    # Grootheid.Code -> CONST_CODE
    # Hoedanigheid.Code -> CONST_PROPERTY

    # print("validate_location [selected]")
    # print("validate_location [selected].loc[0]")
    # print(selected.loc[0])
    # print("validate_location data[location]")
    # print(data["location"])
    # print(selected)

    # oorpronkelijk = selected.loc[0]
    # input = urllib.parse.urlencode(oorpronkelijk)

    # print("Oorpronkelijk")
    # print(oorpronkelijk)
    # print("In")
    # print(input)
    # print("Out")
    # print(urllib.parse.parse_qsl(input))

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
                    vol.Required(CONST_STATION): str,
                    vol.Required(CONST_CODE): str,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
