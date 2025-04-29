"""
Generates the locations.py-file for the WaterInfo HA-integration
"""

import ddlpy
from datetime import datetime as dt, timedelta

doc_dir = ''

# Pull all locations from the DDL-API and sort by alphabet    
locations = ddlpy.locations()
locations = locations.sort_index()

s = open(doc_dir + "locations.py", "w")
s.write('"""Locations for the RWS waterinfo integration."""')
s.write("\n\n")
s.write('CONF_LOC_OPTIONS = [')
s.write("\n")

seen = []
added = []

end = dt.today()
start = end - timedelta(days=14)

# Walk trough all locations
for index, row in locations.iterrows():
    if index == "PORTZLDBSD":
        label = 'PORT ZELANDE'
    else:
        label = row['Naam']

    key = index +"|"+ row["Grootheid.Code"]

    # If
    # - the combination of location and measurement not already checked
    # - location (index) not already in de list
    # - there is a measurement present
    if key not in seen and index not in added:        
        seen.append(key)
        
        if row["Grootheid.Code"] not in ("WATHTBRKD","WATHTEASTRO","WATHTEVERWACHT","QVERWACHT", "NVT"):
            measurements = ddlpy.measurements(row, start, end)

            # Check if there is a measurement the last 14 days            
            if len(measurements) > 0:
                s.write('    {"label": "'+ label + '", "value": "'+ index +'"},')
                s.write("\n")

                # Print debug-measage
                print(index +"|"+ row["Grootheid.Code"])

                added.append(index)

s.write(']')
s.close()
