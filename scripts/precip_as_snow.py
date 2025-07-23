# Parse arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-f", type=str, help="folder for the rasters")
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-o", type=str, help="the output folder for by station results")
# parser.add_argument("-sy", type=int, help="start year")
# parser.add_argument("-ey", type=int, help="end year")
parser.add_argument("-t", type=str, help="gridded threshold form Jenson 2017")
# parser.add_argument("-res", type=str, help="daily (default) or month(ly) resolution")
parser.add_argument("-id",type = str, default = "mvm_id", help = "id variable")

args = parser.parse_args()
# date_range = slice(f"{args.sy}-01-01", f"{args.ey}-12-31")
catch_file = args.c
folder_SMHI = args.f
# resolution = args.res
file_threshold = args.t
output_dir = args.o
#%%
import pandas as pd
import geopandas as gpd
import os
#%%

# output_dir = "/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/03_processed_data/inter_climate" 
# catch_file = "/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/02_raw_data/catchments/merged_catchments/merged_catchments.shp" 
# folder_SMHI= "/home/anlr0006/mnt/anna/My Documents/04_Projects/09_General/03_data/DOC_catchments/input/SMHI" 
# file_threshold =  "/home/anlr0006/mnt/anna/My Documents/04_Projects/09_General/01_GIS/Jennings_2019/jennings_et_al_2018_file4_temp50_raster.tif"
# catch_file = "/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/02_raw_data/catchments/merged_catchments/merged_catchments.shp"
# file_thresholds = "/home/anlr0006/mnt/anna/My Documents/04_Projects/09_General/01_GIS/Jennings_2019/jennings_et_al_2018_file4_temp50_raster.tif"
# folder_SMHI = "/home/anlr0006/mnt/anna/My Documents/04_Projects/09_General/03_data/DOC_catchments/input/SMHI/"
# output_dir = "~/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/03_processed_data/inter_climate/by_station"
#%%

# select which variable is your id column in the, in my case its called mvm_id. This is to loop through all the ids of your shapefile.
id_var = 'mvm_id' 

# change directory to the folder containing your input files and give the names of your input files. 


import os
import shutil

precipitation_path = os.path.join(folder_SMHI, "SMHI_pthbv_pr_1980_2024_daily.nc")
temperature_path = os.path.join(folder_SMHI,"SMHI_pthbv_tas_1980_2024_daily.nc")
# %%
if catch_file.endswith('.zip'):
    cats = gpd.read_file(f"zip://{catch_file}")
    
else:
    cats = gpd.read_file(catch_file)
# cats = cats.iloc[1000:1003]
#%%

input_SMHI_dir = os.path.join("/home/anlr0006/code/DOC_catchments", "input", "SMHI")
os.makedirs(input_SMHI_dir, exist_ok=True)

def ensure_local_copy(filepath):
    filename = os.path.basename(filepath)
    dest_path = os.path.join(input_SMHI_dir, filename)
    
    # Check if destination file already exists
    if os.path.isfile(dest_path):
        print(f"File {dest_path} already exists, skipping copy.")
        return dest_path
    
    # If source and destination are different, copy the file
    if os.path.abspath(filepath) != os.path.abspath(dest_path):
        print(f"Copying {filepath} to {dest_path}")
        # shutil.copy2(filepath, dest_path)
    else:
        print(f"File {filepath} already in target directory.")
    
    return dest_path

# Make sure the files are copied to input/SMHI and update the paths
precipitation_path = ensure_local_copy(precipitation_path)
temperature_path = ensure_local_copy(temperature_path)
file_threshold = ensure_local_copy(file_threshold)

# Validate files exist after copying
if not os.path.isfile(precipitation_path):
    raise FileNotFoundError(f"The precipitation file path {precipitation_path} does not exist.")
if not os.path.isfile(temperature_path):
    raise FileNotFoundError(f"The temperature file path {temperature_path} does not exist.")
if not os.path.isfile(file_threshold):
    raise FileNotFoundError(f"The thresholds file path {file_threshold} does not exist.")

# Path exists
#%% find threshold values
import xarray as xr
import os
import numpy as np
from shapely.geometry import Polygon

cats.to_crs("EPSG:3021", inplace=True) 
# ds = xr.open_dataset(precipitation_path, decode_coords="all")
# ds.rio.write_crs("EPSG:3021", inplace=True) # Ensure ds is in same crs as cats
#%%
import os
import gc
import xarray as xr
import pandas as pd

def process_catchment(row, crs, precipitation_path, temperature_path, file_thresholds, output_dir):
    import rioxarray  # ensure this is available inside multiprocessing environments

    mvm_id = row.mvm_id
    geom = row.geometry
    print(f"🟢 Working on catchment: {mvm_id}")

    try:
        # Load precipitation dataset lazily
        ds = xr.open_dataset(precipitation_path, decode_coords="all", chunks={"time": 100})
        clipped_ds = ds.rio.clip([geom], crs, drop=True, all_touched=True, from_disk=True)
        del ds

        # Load temperature lazily and reproject
        temperature = xr.open_dataset(temperature_path, decode_coords="all", chunks={"time": 100})
        temperature.rio.write_crs("EPSG:3021", inplace=True)

        threshold = xr.open_dataset(file_thresholds, decode_coords="all")  # no time dimension, usually small
        threshold.rio.write_crs("EPSG:4326", inplace=True)

        temperature_proj = temperature.rio.reproject_match(clipped_ds)
        thresholds_proj = threshold.rio.reproject_match(clipped_ds)

        del temperature, threshold

        # Convert time to daily (truncates timestamp)
        clipped_ds["time"] = xr.DataArray(clipped_ds["time"].values.astype("datetime64[D]"), dims="time")
        temperature_proj["time"] = xr.DataArray(temperature_proj["time"].values.astype("datetime64[D]"), dims="time")

        # Merge precipitation and temperature
        clipped_ds = xr.merge([clipped_ds, temperature_proj])
        del temperature_proj

        # Merge threshold (drop band dimension)
        clipped_ds = xr.merge([clipped_ds, thresholds_proj.isel(band=0)])
        del thresholds_proj

        # Compute snow precipitation
        clipped_ds["pr_snow"] = xr.where(clipped_ds["tas"] <= clipped_ds["band_data"], clipped_ds["pr"], 0)
        clipped_ds["pr_snow"].attrs['units'] = 'kg water / m^2'
        clipped_ds["pr_snow"].attrs['long_name'] = 'Precipitation as snow'

        # Spatial average and convert to DataFrame
        result = clipped_ds.mean(dim=["x", "y"]).drop_vars(["crs", "band", "spatial_ref"]).to_dataframe()
        result['mvm_id'] = mvm_id
        result['date'] = result.index

        # Save result
        return result


    except Exception as e:
        print(f"❌ ERROR in catchment {mvm_id}: {e}")

    finally:
        # Free memory
        del clipped_ds
        gc.collect()

    # return result
#%%
crs = cats.crs
#%%
os.makedirs(output_dir, exist_ok=True)
print(f" Path: {output_dir} \n {os.path.exists(output_dir)}")

import os
import subprocess
import tempfile
import pandas as pd

for idx, row in cats.iterrows():
    target_path = os.path.join(output_dir, f"{row['mvm_id']}.csv")

    if os.path.exists(target_path):
        print(f"catchment {row['mvm_id']} already exists.")
        continue  # skip to next row

    # Create an empty placeholder file (optional, can skip if you prefer)
    try:
        with open(target_path, 'w') as fp:
            pass
    except PermissionError:
        # Can't create file directly due to permissions — that's expected, no worries
        pass

    try:
        # Run your processing function; expect a DataFrame return
        df_result = process_catchment(row, crs, precipitation_path, temperature_path, file_threshold, output_dir)

        # Save to temp file first
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            temp_path = tmp_file.name
            df_result.to_csv(temp_path, index=False)

        # Move temp file to target with sudo
        subprocess.run(['sudo', 'mv', temp_path, target_path], check=True)
        print(f"Saved catchment {row['mvm_id']} successfully.")

    except Exception as e:
        # Cleanup temp file if exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

        # Cleanup target file if created partially (may require sudo)
        try:
            subprocess.run(['sudo', 'rm', '-f', target_path], check=True)
        except Exception:
            print(f"Could not remove file {target_path}")

        print(f"⚠️ Error processing catchment {row['mvm_id']} at index {idx}: {e}")

#%%

# # Check for missing days in the clipped_ds time series
# time_index = pd.to_datetime(result['date'].values)
# full_range = pd.date_range(start=time_index.min(), end=time_index.max(), freq='D')
# missing_days = full_range.difference(time_index)

# print(f"Total days in range: {len(full_range)}")
# print(f"Days present in data: {len(time_index)}")
# print(f"Missing days: {len(missing_days)}")
# if not missing_days.empty:
#     print("Missing dates:", missing_days)
# else:
#     print("No missing days in the time series.")

# # can you plot the days so i can see where they are missing

# pd.DataFrame(missing_days, columns=["missing_days"]).to_csv("temp.csv", index=False)

    # x = clipped_ds.sizes['x']
    # y = clipped_ds.sizes['y']
    # # Check if the clipped_ds has less than 2 grid cells in x or y, and if so, buffer the geometry and redo the clip
    # if (x < 2) or (y < 2):
    #     del clipped_ds
    #     del geom
    #     del ds
    #     print("Buffering geometry due to insufficient grid cells." )
    #     geom = cats.iloc[i].geometry
    #     geom = geom.buffer(1000)  # Buffer by 100 meters
    #     ds = xr.open_dataset(precipitation_path, decode_coords="all")
    #     ds.rio.write_crs("EPSG:3021", inplace=True)
    #     clipped_ds = ds.rio.clip([geom], cats.crs, drop=True, all_touched=True)
    #     x = clipped_ds.sizes['x']
    #     y = clipped_ds.sizes['y']

    # if (x < 2) or (y < 2):
    #     print("Buffering geometry due to insufficient grid cells a second time." )
    #     del clipped_ds
    #     del geom
    #     del ds
    #     print("Buffering geometry due to insufficient grid cells." )
    #     geom = cats.iloc[i].geometry
    #     geom = geom.buffer(500)  # Buffer by 100 meters
    #     ds = xr.open_dataset(precipitation_path, decode_coords="all")
    #     ds.rio.write_crs("EPSG:3021", inplace=True)
    #     clipped_ds = ds.rio.clip([geom], cats.crs, drop=True, all_touched=True)
    #     x = clipped_ds.sizes['x']
    #     y = clipped_ds.sizes['y']

    # clipped_ds