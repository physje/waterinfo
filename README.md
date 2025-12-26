# Rijkswaterstaat Waterinfo #

The Dutch Department of Waterways and Public Works (Rijkswaterstaat in Dutch) has the website [Waterinfo](https://waterinfo.rws.nl/#/nav/publiek) where all kind of water data is available. This includes information about water levels, water temperatures, wave heights, wind speed, etc.
These measurements are update frequently (like every 10 minutes).

This integration uses the API of Waterinfo to fetch data from a particular location into a Home Assistant entity with sensors for all measurements on that location.

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=waterinfo&owner=physje)

or

1. Search for the "Rijkswaterstaat waterinfo" integration in HACS. It will be automatically installed to the `custom_components` directory
2. Restart Home Assistant.
3. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Rijkswaterstaat Waterinfo"
4. Follow the UI based Configuration

### Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `waterinfo`.
4. Download _all_ the files from the `custom_components/waterinfo/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Rijkswaterstaat Waterinfo"

## Configuration is done in the UI

You can configure and setup the Waterinfo integration in your integrations page, look for "Rijkswaterstaat Waterinfo" in the add integrations dialog.

To configure a sensor, just select the location of your choice in the pull-down-menu and press 'Next'. Not all measurements are available at all locations. An overview of which measurement is available for which location is given in the `docs`-folder. There are pages with the overview based on location (eg [Locations with a A](docs/location_A.md)) and pages with the overview based on measurement (eg [Measuements with a C](docs/measurement_C.md)).

If you are for example are a windsurf-fan and you wants to make an entity with sensors for different water-measurements in the middle of the Lake IJssel, you select **Markermeer Midden -o** and an entity with sensors for all measurements on that location will be created. Two of them are a sensor for **Windsnelheid Lucht t.o.v. Mean Sea Level in m/s** and a sensor for **Significante golfhoogte in het spectrale domein Oppervlaktewater golffrequentie tussen 30 en 500 mHz in cm**. If you're not interested in the other sensors: just disable them afterwards.

Not all sensors are enabled by default. If it's not a measurement but an expectation (means multiple points, or value in the future) the sensor is disabled by default. The same is true if there are no measurements present in the last 14 days. A soon as there are measurements available, you can enable the sensor to pull there measurements.

## Known limitations

 - The integration does not work properly for pre-2023.9-versions of Home Assistant.
 - This integration is translated into English, German and Dutch, the entity names and the data (from the API) are only available in Dutch.
 - Sometimes the Rijkswaterstaat site is down for inexplicable reasons. At that moment, creating new entities is impossible and entities/sensors that already exist will not be updated.
