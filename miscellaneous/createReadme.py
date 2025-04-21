"""
This file generates the files in de docs-folder
"""

import ddlpy
from datetime import datetime as dt, timedelta
import math
import pandas as pd
import os
import pytz

utc=pytz.UTC

end_date = dt.today()
start_date = end_date - timedelta(days=7)

doc_dir = ''

seen = []
measurements = {}
grootheid = {}
descr = {}
locArray = {}
vorige_index = ''
ref_loc_all = []
ref_meas_all = []

start = dt.now()

# Locations start with all letters of the alphabet
# Measurements only with a few
alfabet_loc = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
alfabet_meas = ['C','F','G','H','L','Q','S','T','W','Z'] 

# Generate an array with hyperlinks to all location-pages
# This array will be used on the measurement-pages
for letter_L in alfabet_loc:
    ref_loc_all.append("[%s](%s)" % (letter_L, "location_"+ letter_L +".md"))

# Generate an array with hyperlinks to all measurement-pages
# This array will be used on the location-pages
for letter_M in alfabet_meas:
    ref_meas_all.append("[%s](%s)" % (letter_M, "measurement_"+ letter_M +".md"))

# Generate all "empty" location-pages (contains only the header)
# Header contains hyperlinks to all other location- and measurement-pages
for letter_L in alfabet_loc:
    ref_loc = []    
    for link_L in alfabet_loc:
        if letter_L == link_L :
            ref_loc.append(link_L)
        else :
            ref_loc.append("[%s](%s)" % (link_L, "location_"+ link_L +".md"))

    s = open(doc_dir + "location_"+ letter_L +".md", "w")
    s.write("Locations : ")
    s.write(" | ".join(ref_loc))    
    s.write("\n\n")
    s.write("Measurements : ")
    s.write(" | ".join(ref_meas_all))    
    s.write("\n\n")
    s.write("# Locations with the letter "+ letter_L +" #\n\n")
    s.close()

# Generate all "empty" measurement-pages (contains only the header)
# Header contains hyperlinks to all other location- and measurement-pages
for letter_M in alfabet_meas:
    ref_meas = []

    for link_M in alfabet_meas:
        if letter_M == link_M :
            ref_meas.append(link_M)
        else :
            ref_meas.append("[%s](%s)" % (link_M, "measurement_"+ link_M +".md"))

    s = open(doc_dir + "measurement_"+ letter_M +".md", "w")
    s.write("Locations : ")
    s.write(" | ".join(ref_loc_all))    
    s.write("\n\n")
    s.write("Measurements : ")
    s.write(" | ".join(ref_meas))    
    s.write("\n\n")
    s.write("# Measurements with the letter "+ letter_M +" #\n\n")
    s.close()    

# Pull all locations from the DDL-API and sort by alphabet    
locations = ddlpy.locations()
locations = locations.sort_index()

#locations = locations[:100]

# Walk trough all locations
for index, row in locations.iterrows():    
    # T can be water-temperature and air-temperature
    # So generate a unique key
    key = index +"|"+ row["Grootheid.Code"]
    
    # Check of this key (which is a combination of location en measurement) already exist
    # If not, continue
    if key not in seen :        
        seen.append(key)
        letter_s = key[0]
        s = open(doc_dir + "location_"+ letter_s +".md", "a")

        # Print debug-measage        
        print(index +"|"+ row["Grootheid.Code"])

        # If measurement exist, continue    
        if row["Grootheid.Code"] != 'NVT' and index[0:4] != 'VERD':
            # Check if there is recent data
            data = ddlpy.measurements_latest(row)
            tijdstip_datetime = dt.strptime(data["Tijdstip"].iloc[0], '%Y-%m-%dT%H:%M:%S.%f%z')            
            if tijdstip_datetime > utc.localize(start_date):
                if index != vorige_index:
                   
                    # It has something to do with the chartype, but PORT ZELANDE always gives an error
                    # Quick and dirty solution
                    if index == "PORTZLDBSD" :
                        s.write("\n## PORT ZELANDE ##\n")
                    else:
                        s.write("\n## "+ row["Naam"] +" ##\n")

                    # Write location-information to the location-page
                    s.write("|Measurement|\n")
                    s.write("|---|\n")

                # Write measurement-information to the location-page
                s.write("|"+ row["Parameter_Wat_Omschrijving"] +"|\n")
                s.close()
                vorige_index = index

                # Store unique key in locArray, an array used to generate pages based on measurements
                if index not in locArray:
                    locArray[index] = row["Naam"]

                # Generate index for storage in measurement-array
                measIndex = row["Grootheid.Code"]+row["Parameter_Wat_Omschrijving"][13:18]

                if measIndex in measurements:
                    indices = measurements[measIndex]               
                else:
                    indices = []
                    descr[measIndex] = row["Parameter_Wat_Omschrijving"]
                    grootheid[measIndex] = row["Grootheid.Code"]
    
                indices.append(index)
                measurements[measIndex] = indices

# Walk trough the measurements-array to generate pages based on measurements         
for key in measurements:
    letter_m = key[0]
    m = open(doc_dir + "measurement_"+ letter_m +".md", "a")

    # Write header
    m.write("## "+ descr[key] +" ##\n")
    m.write("|Location|\n")
    m.write("|---|\n")

    # Get all locations which does have this measurement
    # and write it to the measurement-page
    locations = measurements[key]
        
    for loc in locations:
        #m.write("|"+ locArray[loc] +"|"+ loc +"|\n")
        m.write("|"+ locArray[loc] +"|\n")

    m.write("\n\n")
    m.close()

# Write footer for both type of pages
for letter in alfabet_loc:
    s = open(doc_dir + "location_"+ letter +".md", "a")
    s.write("\n\n")
    s.write("_generated on "+ end_date.strftime("%d-%m-%Y") +"_")
    s.close()
    
for letter in alfabet_meas:
    s = open(doc_dir + "measurement_"+ letter +".md", "a")
    s.write("\n\n")
    s.write("_generated on "+ end_date.strftime("%d-%m-%Y") +"_")
    s.close()

end = dt.now()

print(start)
print(end)
