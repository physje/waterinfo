_Component to integrate with [Waterinfo](https://waterinfo.rws.nl/#/nav/publiek)._

This custom component creates one sensor.waterinfo_* item for every configured observation. You can add as many sensors (ie observations) as you want. 

**This component will set up the following platforms.**

Platform | Description
`sensor` | one sensor for every configured location-measurement-combination.



{% if not installed %}
## Installation

1. Click install.
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "waterinfo".

{% endif %}


## Configuration is done in the UI