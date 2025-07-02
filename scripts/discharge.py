#%%
import geopandas as gpd
import os

#os.chdir("..")
# load catchments
gdf_catch = gpd.read_feather("results\\SVAR\\catch_316_ARO.feather")

# %%
# extract just the stations from the catchments
# stations = gdf_catch[['lat','lon','mvm_id', 'Shape_Area']]

# %%
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt



# Create GeoDataFrame from stations using SWEREF coordinates
gdf = gpd.GeoDataFrame(
    stations,
    geometry=gpd.points_from_xy(stations["lon"], stations["lat"]),
    crs="EPSG:3006"  # SWEREF 99 TM
)
# %%
# # Load SVARO ID's to get upstream area added to the stations and call it gdf
# svaro = gpd.read_file("results/SVARO/aro.gpkg").to_crs("EPSG:3006")
# gdf = gpd.sjoin(gdf, svaro[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']], how='left', predicate='within').drop(columns=['index_right'])
# gdf
#%%
import pandas as pd
# Calculate the weight for the area weighted discharge 
gdf_catch['weight'] = gdf_catch['area_m2']/gdf_catch['AREA_UPSTREAM']

#calculate the lokal weight: if this values is => 1 than the lokal vattenfö.. should be used
gdf_catch['weight_lokal'] = gdf_catch['area_m2']/gdf_catch['AREA'] 
gdf_catch
#gdf.loc[gdf['weight'] < 0.1][['AU_CD', 'mvm_id', 'area_svaro', 'Shape_Area', 'weight', 'lokal_area', 'weight_lokal', 'antal_poly']]
#%%
# Define the input, filtered output, and remaining output file paths
input_file = "\\\\storage.slu.se\\Home$\\anlr0006\\My Documents\\04_Projects\\02_Top-Down\\01_data\\02_raw_data\\02_SMHI\\1991-SMHI_catch_316.csv"
removed_file = 'results/SVAR/S-HYPE_uncertainty_catch_316.txt'
remaining_file = 'results/SVAR/SVARO_discharge_catch_316.csv'

# Ensure the directory exists for the output files
os.makedirs(os.path.dirname(removed_file), exist_ok=True)
os.makedirs(os.path.dirname(remaining_file), exist_ok=True)

# Create the files if they don't exist
for file_path in [removed_file, remaining_file]:
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            pass

# Open the input file for reading
with open(input_file, 'r', encoding='utf-8') as infile:
    lines = infile.readlines()

# Open the two new files for writing
with open(removed_file, 'w', encoding='utf-8') as removed, open(remaining_file, 'w', encoding='utf-8') as remaining:
    for line in lines:
        # Check if the line starts with "Modellosäkerhet"
        if line.startswith('Modellosäkerhet'):
            # Write the line to the removed lines file
            removed.write(line)
        else:
            # Write the remaining lines to the remaining file
            remaining.write(line)

print(f"Lines starting with 'Modellosäkerhet' have been written to: {removed_file}")
print(f"Remaining lines have been written to: {remaining_file}")


#%%
# Load the discharge data from SMHI. This will have been retrieved from putting the ARO_UUID.txt comma seperated list generated in get_SVARO into nadia. then save it here in the results/SVARO as SVAR=_discharge

svaro_discharge = pd.read_csv(remaining_file, sep = ";", decimal= ",", parse_dates= [2] )
svaro_discharge.rename(columns={'Datum' : 'date'}, inplace=True)
#%%

# Find the discharge
pd.options.mode.chained_assignment = None  # default='warn'

discharge = pd.DataFrame(columns=['mvm_id', 'date', 'q', 'area_m2'])
mvm_ids = gdf_catch['mvm_id'].unique()
for id in mvm_ids:
    aroid = gdf_catch.loc[gdf_catch['mvm_id']== id]['ARO_UUID'].values[0]
    lokal_area = gdf_catch.loc[gdf_catch['mvm_id']== id]['AREA'].values[0]
    area = gdf_catch.loc[gdf_catch['mvm_id']== id]['area_m2'].values[0]
    local_q = svaro_discharge.loc[svaro_discharge['Aroid'] == aroid]
    local_q['mvm_id'] = id
    local_q['area_m2'] = area
    weight = gdf_catch.loc[gdf_catch['mvm_id']== id]['weight'].values[0]
    # lokal_weight = gdf_catch.loc[gdf_catch['mvm_id']== id]['weight_lokal'].values[0]
    if (lokal_area > area) & ( weight < 0.1) :
        # print(id)
        weight = gdf_catch.loc[gdf_catch['mvm_id']== id]['weight_lokal'].values[0]
        local_q.loc[:,'q'] = local_q.loc[:,'Lokal vattenföring'] * weight
    else:
        local_q.loc[:,'q'] = local_q.loc[:,'Total stationskorrigerad vattenföring'] * weight
    discharge = pd.concat([discharge, local_q[['mvm_id', 'date','q']]])
discharge.describe()

#%% check for duplicates

duplicates = discharge[discharge.duplicated(subset=['mvm_id', 'date'], keep=False)]
duplicates
# %%
# Ensure the directory exists
import os
os.makedirs("results/discharge", exist_ok=True)

discharge.to_csv("results/discharge/daily_discharge_catch_316.csv", index = False)


# %%
