"""Define services for the Waterinfo integration."""

from datetime import datetime as dt, timedelta
import logging

import ddlpy

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse

from .const import (
    CONF_CONTEXT_PATH,
    DOMAIN,
    SERVICE_LOC_REFRESH,
    SERVICE_NOTIFY,
    SERVICE_REFRESH_ACTIVE,
    SERVICE_REFRESH_CODE,
)

_LOGGER = logging.getLogger(__name__)


def setup_services(hass: HomeAssistant) -> None:
    """Set up the services used by Waterinfo component."""

    async def handle_location_refresh(call: ServiceCall) -> ServiceResponse:
        """Handle the service call."""
        active_only = call.data.get(SERVICE_REFRESH_ACTIVE, True)
        notify = call.data.get(SERVICE_NOTIFY, True)
        with_code = call.data.get(SERVICE_REFRESH_CODE, False)

        await hass.async_add_executor_job(makeLocationFile, active_only, with_code)

        if notify:
            persistent_notification.async_create(
                hass,
                "The locations of the waterinfo-integration are refreshed. Home Assistant should be restarted to take effect",
                "Locations list",
            )

        return None

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOC_REFRESH,
        handle_location_refresh,
    )


def makeLocationFile(active_only, with_code) -> None:
    """Generate new locations.py."""

    locations = ddlpy.locations()
    locations = locations.sort_index()

    s = open(CONF_CONTEXT_PATH + "locations.py", "w", encoding="utf-8")
    s.write('"""Locations for the RWS waterinfo integration."""\n')
    s.write('"""Generated ' + dt.today().strftime("%d-%m-%Y %H:%M:%S") + '."""\n')
    s.write('"""Active only: ' + str(active_only) + '."""\n')
    s.write('"""With code: ' + str(with_code) + '."""\n')
    s.write("\n")
    s.write("CONF_LOC_OPTIONS = [")
    s.write("\n")

    seen = []

    if active_only:
        added = []
        end = dt.today()
        start = end - timedelta(days=14)

    # Walk trough all locations
    for index, row in locations.iterrows():
        if index == "PORTZLDBSD":
            label = "PORT ZELANDE"
        else:
            label = row["Naam"]

        if active_only:
            key = index + "|" + row["Grootheid.Code"]

            if key not in seen and index not in added:
                seen.append(key)

                # All expected and calculated values are no real measurements
                if row["Grootheid.Code"] not in (
                    "WATHTBRKD",
                    "WATHTEASTRO",
                    "WATHTEVERWACHT",
                    "QVERWACHT",
                    "NVT",
                ):
                    # Check if the latest measurement is less than 14 days old
                    measurements = ddlpy.measurements(row, start, end)

                    if len(measurements) > 0:
                        if with_code:
                            s.write(
                                '    {"label": "'
                                + label
                                + " ("
                                + index
                                + ')", "value": "'
                                + index
                                + '"},'
                            )
                        else:
                            s.write(
                                '    {"label": "'
                                + label
                                + '", "value": "'
                                + index
                                + '"},'
                            )
                        s.write("\n")

                        added.append(index)
        elif index not in seen:
            if with_code:
                s.write(
                    '    {"label": "'
                    + label
                    + " ("
                    + index
                    + ')", "value": "'
                    + index
                    + '"},'
                )
            else:
                s.write('    {"label": "' + label + '", "value": "' + index + '"},')
            s.write("\n")

            seen.append(index)

    s.write("]")
    s.close()

    return True
