import pandas as pd
import folium
from folium.plugins import MarkerCluster
import os
import requests
import re

#
# GEOCODING
#

os.chdir('/navigate_to/your_data_folder/')
df = pd.read_csv('address.csv', index_col='participantId')

# casting string type onto all fields containing address, e.g. field1 contains street, field2 contains city etc.
types_dict = {'field1': str, 'field2': str, 'field3': str, 'field4': str}
for col, col_type in types_dict.items():
    df[col] = df[col].astype(col_type)

# combine columns containing address together into one column named 'full address'
df['full_address'] = df[['field1', 'field3', 'field4', 'field5']].agg(','.join, axis=1)

URL = "https://geocode.search.hereapi.com/v1/geocode"
api_key = '' # insert your API key here

for index, row in df.iterrows():
    location = row.full_address
    if 'nan' in location:
        print('No address for row: ', index, location)
    else:
        PARAMS = {'apikey': api_key, 'q': location}
        r = requests.get(url=URL, params=PARAMS)
        data = r.json()

        df.at[index, 'lat'] = data['items'][0]['position']['lat']
        df.at[index, 'lon'] = data['items'][0]['position']['lng']

df.to_csv('address_geocoded.csv')

#
# ADDITIONAL CONFIRMATION
# If there is GPS tracking data, this can determine if a median nighttime location differs from the geocoded
# house address. It prints all cases where geocoded latitude and longitude is substantially different from the nighttime
# median (difference larger than ~37.4 meters, or 0.0003 degrees WGS 1984)
#

big_differences = []
errors = []

for file_name in os.listdir(): # go through the folder with the GPS data
    num = re.search(r'\d{4}', file_name)  # extract person's ID number from the file name. Here we have ID of 4 numbers
    if num and 'csv' in file_name:
        try:
            num_participant = int(num.group())
            log = pd.read_csv(file_name, parse_dates=['timestamp'], infer_datetime_format=True) #parses time in the timestamp folder
            lat_geocoded = df.loc[num_participant].lat
            lon_geocoded = df.loc[num_participant].lon

            # log_nighttime returns a dataframe with all entries for 12am-4am times and with speed less than 1 (idle)
            log_nighttime = log[(log.timestamp.dt.hour <= 4) & (log.speed < 1)]
            lat_gps = log_nighttime.lat.median()
            lon_gps = log_nighttime.lon.median()

            lat_diff = abs(lat_gps - lat_geocoded)
            lon_diff = abs(lon_gps - lon_geocoded)
            if lat_diff < 0.0003 and lon_diff < 0.0003:
                # median nighttime gps location doesnt differ much from the geocoded house address
                continue
            else:
                # big discrepancy between the median nighttime gps location and the geocoded one.
                # either due to incorrect geocoding of the house address or a person did not stay often at their
                # house address at night
                print(num_participant)
                print('geocoded:', lat_geocoded, lon_geocoded),
                print('gps: ', lat_gps, lon_gps, '\n')
                big_differences.append(num_participant)
        except Exception as e:
            errors.append(num_participant)
            print(num_participant)
            print('Could not execute.  ', getattr(e, 'message', repr(e)), '\n')


#
# ADDITIONAL CONFIRMATION - MAPPING
# We can visualize clusters of nighttime GPS tracking and a house address on a map as well to see how far away the
# points are and what is the pattern in the data
#

num_participant = big_differences[0]  # as an example, take the first person from the list of everyone with large differences. This will be their ID number
log = pd.read_csv(+str(num_participant)+'.csv',
                      parse_dates=['timestamp'], infer_datetime_format=True)
lat_geocoded = df.loc[num_participant].lat
lon_geocoded = df.loc[num_participant].lon

log_nighttime = log[(log.timestamp.dt.hour <= 4) & (log.speed < 1)]  # & (log.timestamp.dt.minute <5)
locationlist = list(zip(log_nighttime.lat.tolist(), log_nighttime.lon.tolist()))

# Create a map centered at the house address
m = folium.Map(location=(lat_geocoded, lon_geocoded), zoom_start=12, tiles='CartoDB positron')
marker_cluster = MarkerCluster().add_to(m)

locationlist = list(zip(log_nighttime.lat.tolist(), log_nighttime.lon.tolist()))
# add clusters of GPS points to the map
for point in range(0, len(locationlist)):
    folium.Marker(locationlist[point], popup='{}, {}'.
                  format(big_differences[point][0], big_differences[point][1])).add_to(marker_cluster)

# add a marker point to the map of the house
folium.Marker(location=[lat_geocoded, lon_geocoded], popup='Baseline', icon=folium.Icon(color='green')).add_to(m)
