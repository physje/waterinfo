"""Constants for the RWS waterinfo integration."""

DOMAIN = "waterinfo"
MIN_HA_VERSION = "2023.09"

CONST_LOC_CODE = "loc_code"  # DEVE
CONST_LOC_NAME = "loc_name"  # Naam / Deventer
CONST_MEAS_CODE = "meas_code"  # Grootheid.Code / WATHTE
CONST_MEAS_NAME = "meas_name"  # Grootheid.Omschrijving / Waterhoogte
CONST_MEAS_DESCR = "meas_descr"  # Parameter_Wat_Omschrijving / Waterhoogte Oppervlaktewater t.o.v. Normaal Am
CONST_UNIT = "unit"  # Eenheid.Code / cm
CONST_COMP_CODE = "comp_code"  # Compartiment.Code / OW
CONST_COMP_NAME = "comp_name"  # Compartiment.Omschrijving / Oppervlaktewater
CONST_PROP = "property"  # Hoedanigheid.Code / NAP
CONST_LONG = "long"  # X
CONST_LAT = "lat"  # Y
CONST_COORD = "coord"
CONST_ENABLE = "enable"
CONST_PROCES_TYPE = "proces_type"
CONST_SENSOR_UNIQUE = "sensor_ID"
CONST_DEVICE_UNIQUE = "device_ID"
CONST_SENSOR = "sensoren"
CONST_MULTIPLIER = "multiplier"
CONST_EXPEC_TYPE = "expectation_type"

ATTR_LAST_DATA = "last_data"
ATTR_LAST_CHECK = "last_check"
ATTR_PREDICT_TIME = "predicted_time"

OPT_TIMEDELTA = "time_delta"
DEFAULT_TIMEDELTA = 14
MIN_TIMEDELTA = 1
API_TIMEZONE = 1

PEAK_DISTANCE = (
    30  # Minimum points between tides (5 hours, 10-min intervals = 5*6 = 30)
)
PEAK_PROMINENCE = 5  # Minimum height difference in cm
CACHE_DURATION = 300

CONF_LOC_SELECTOR = "Selecteer plaats"

CONF_CONTEXT_PATH = "/config/custom_components/waterinfo/"

SERVICE_LOC_REFRESH = "renew_locations"
SERVICE_REFRESH_ACTIVE = "active_only"
SERVICE_REFRESH_CODE = "with_code"
SERVICE_NOTIFY = "notify"

# I always forget the syntax, so I place it here
# python -m script.hassfest --integration-path homeassistant/components/waterinfo --skip-plugins quality_scale
