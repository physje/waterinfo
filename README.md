# Rijkswaterstaat Waterinfo #

The Dutch Department of Waterways and Public Works (Rijkswaterstaat in Dutch) has the website [Waterinfo](https://waterinfo.rws.nl/#/nav/publiek) where you can see all kind of water data. This includes information about water levels, water temperatures, wave heights, wind speed, etc.
The data is update frequently (like every 10 minutes).

This integration uses the API of Waterinfo to fetch data from a particular location and subject (like waterlevel in a river at a specific location) into a Home Assistant sensor.

## Installation

### HACS

This component can be installed in your Home Assistant with HACS.


### Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `waterinfo`.
4. Download _all_ the files from the `custom_components/waterinfo/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "waterinfo"

## Configuration is done in the UI

You can configure and setup the Waterinfo integration in your integrations page, look for Waterinfo in the add integrations dialog.

To configure a sensor, you need to know the code for the location and the code for the measurement. An overview of which measurement is available for which location is given in the `docs`-folder. There are pages with the overview based on location (eg [Locations with a A](docs/location_A.md)) and pages with the overview based on measurement (eg [Measuements with a C](docs/measurement_C.md)).

If you are for example are a windsurf-fan and you wants to make a sensor for the windspeed in the middle of the Lake IJssel, you need to know the waterinfo-code for that location and the waterinfo-code for the measurement.
On [Measuements with a W](docs/measurement_W.md) or [Locations with a F](docs/location_F.md) you can see that the measurement-code for **Windsnelheid Lucht t.o.v. Mean Sea Level in m/s** is _WINDSHD_ and the location-code for **Markermeer Midden -o** is _FL42o_ (both codes are case-sensitive).
In the same way on [Measuements with a T](docs/measurement_T.md) or [Locations with a T](docs/location_T.md) the codes for air-temperatur on the Terschelling can be found to be (measurement-code : _T_; location-code : _TERS_).


## Known limitations

 - This integration is translated into English and Dutch, the entity names and the data (from the API) are only available in Dutch.
 - Sometimes the Rijkswaterstaat site is down for inexplicable reasons. At that moment, creating new sensors is impossible and sensors that have already exist will not be updated.

## Examples

t