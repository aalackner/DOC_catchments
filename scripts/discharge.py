#%%
import argparse
parser = argparse.ArgumentParser()
# parser.add_argument("-c", type=str, help="the catchments either as .zip containing shp  or shp file")
parser.add_argument("-o", type=str, help="the output folder, for ids and .feather used in discharge.py")
parser.add_argument("-id", type=str, default = 'mvmid' ,help="the unique id column in the catchment shapefile")
parser.add_argument("-f", type=str, default = "2025-data.csv", help="file name of the NADIA output")

args = parser.parse_args()
# file_catch = args.c
output_folder = args.o
id_var = args.id
file_nadia = args.f
#%%
import geopandas as gpd

# file_catch = "../data/test.shp"
# output_folder = "../test_results/runoff"
# x_coord = "x_utlopp"
# y_coord = "y_utlopp"
# id_var = "id"
# file_nadia = "2025-data.csv"
# file_map = "true"

#%%
import geopandas as gpd
import os

feather_path = os.path.join(output_folder, "cats_svar2022.feather")
#os.chdir("..")
# load catchments
gdf_catch = gpd.read_feather(feather_path)

print(gdf_catch[id_var].nunique())

#%%
import pandas as pd
# Calculate the weight for the area weighted discharge 
gdf_catch['weight'] = gdf_catch['area_m2']/gdf_catch['AREA_UPSTREAM']

#calculate the lokal weight: if this values is => 1 than the lokal vattenfö.. should be used
gdf_catch['weight_lokal'] = gdf_catch['area_m2']/gdf_catch['AREA'] 
gdf_catch
#gdf.loc[gdf['weight'] < 0.1][['AU_CD', id_var, 'area_svaro', 'Shape_Area', 'weight', 'lokal_area', 'weight_lokal', 'antal_poly']]
#%%
# Define the input, filtered output, and remaining output file paths
input_file = os.path.join(output_folder, file_nadia)


removed_file = os.path.join(output_folder, 'SVAR/S-HYPE_uncertainty.txt')
remaining_file = os.path.join(output_folder, 'SVAR/SVARO_discharge.csv')
#%%
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

import pandas as pd
import re

# Path to your txt file

# Pattern to extract the needed values
pattern = re.compile(
    r"Modellosäkerhet (\d+\.?\d*)% och (\d+\.?\d*)% .*?subid (\d+), MQ (\d+\.?\d*)"
)

# Store parsed rows
rows = []

# Read and parse file
with open(removed_file, "r", encoding="utf-8") as f:
    for line in f:
        match = pattern.search(line)
        if match:
            perc1, perc2, subid, mq = match.groups()
            rows.append({
                "subid": int(subid),
                "MQ": float(mq),
                "model_uncertainty": float(perc1),
                "model_uncertainty_station_corrected": float(perc2)
            })

# Convert to DataFrame
uncertainty = pd.DataFrame(rows)

# Show table
# uncertainty

#%%
# Find the discharge
pd.options.mode.chained_assignment = None  # default='warn'

discharge = pd.DataFrame(columns=[id_var, 'date', 'q', 'Subid'])
mvm_ids = gdf_catch[id_var].unique()
for id in mvm_ids:
    aroid = gdf_catch.loc[gdf_catch[id_var]== id]['ARO_UUID'].values[0]
    lokal_area = gdf_catch.loc[gdf_catch[id_var]== id]['AREA'].values[0]
    area = gdf_catch.loc[gdf_catch[id_var]== id]['area_m2'].values[0]
    local_q = svaro_discharge.loc[svaro_discharge['Aroid'] == aroid]
    local_q[id_var] = id
    local_q['area_m2'] = area
    weight = gdf_catch.loc[gdf_catch[id_var]== id]['weight'].values[0]
    # lokal_weight = gdf_catch.loc[gdf_catch[id_var]== id]['weight_lokal'].values[0]
    if (lokal_area > area) & ( weight < 0.1) :
        # print(id)
        weight = gdf_catch.loc[gdf_catch[id_var]== id]['weight_lokal'].values[0]
        local_q.loc[:,'q'] = local_q.loc[:,'Lokal vattenföring'] * weight
    else:
        local_q.loc[:,'q'] = local_q.loc[:,'Total stationskorrigerad vattenföring'] * weight
    discharge = pd.concat([discharge, local_q[[id_var, 'date','q', 'Subid', 'area_m2']]])


discharge = discharge.merge(
    uncertainty.rename(columns={'subid': 'Subid'})
               .drop(columns=['model_uncertainty', 'MQ']),
    on='Subid',
    how='left'
)
#%% check for duplicates

duplicates = discharge[discharge.duplicated(subset=[id_var, 'date'], keep=False)]

# %%
# Ensure the directory exists

import os
print(discharge[id_var].nunique())


out_file = os.path.join(output_folder, "daily_discharge.csv")
discharge.to_csv(out_file, index = False)
