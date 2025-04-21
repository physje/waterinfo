"""
Generates the locations.py-file for the WaterInfo HA-integration
"""

import ddlpy

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

# Walk trough all locations
for index, row in locations.iterrows():    
    if index == "PORTZLDBSD":
        label = 'PORT ZELANDE'
    else:
        label = row['Naam']

    if index not in seen:        
        s.write('    {"label": "'+ label + '", "value": "'+ index +'"},')
        s.write("\n")

        seen.append(index)

s.write(']')
s.close()
