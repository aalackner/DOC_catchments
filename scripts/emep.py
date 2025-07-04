# script for calculating the deposition from EMEP data
# Parse arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-f", type=str, help="folder for the input ncs")
parser.add_argument("-c", type=str, help="the catchments either as .zip containing shp  or shp file")
parser.add_argument("-o", type=str, help="the output file")
parser.add_argument("-id", type=str, default = 'mvmid' ,help="the unique id column in the catchment shapefile")
parser.add_argument("-sy", type=int, help="start year")
parser.add_argument("-ey", type=int, help="end year")
parser.add_argument("-d", type=str, default = "False" , help="download of data required True or False: True will download the data from the thredds.met.no server")


args = parser.parse_args()
catch_file = args.c

if args.d not in ["True", "False"]:
    raise "-d must be either True or False, default behaviour is set to False"

if (args.sy in range(1990, 2023)) and (args.ey > args.sy):
    date_range = range(args.sy, args.ey)
else: 
    raise "Please enter a valid date range between 1990 and 2023"

import geopandas as gpd

try: 
    if catch_file.endswith(".shp"):
        catch_gdf = gpd.read_file(catch_file)
    else:
        catch_gdf = gpd.read_file(f"zip://{catch_file}")
except ValueError: 
    print("Please enter a valid catchment file. either as a .sho or .zip containing the .shp with the same name as the .zip")


output_file = args.o



#%%  Lets have a look at the example file 
from shapely.geometry import Polygon
import os
import rioxarray # initiated rioxarray GIS refernced xarrays (Is needed!)
import xarray as xr
from shapely.geometry import mapping
import pandas as pd
import numpy as np
import requests

#%% downloading the EMEP data for the years 1990-2020 

### ONLY RUN ONCE, to download the data #####
output_dir = args.f

if args.d == "True":
    base_url = "https://thredds.met.no/thredds/fileServer/data/EMEP/2024_Reporting/EMEP01_rv5.3_month.{year}met_{year}emis_rep2024.nc"
    
    os.makedirs(output_dir, exist_ok=True)

    for year in date_range:
        if year == 2022:
        # For 2022, use the specific file
            url = "https://thredds.met.no/thredds/fileServer/data/EMEP/2024_Reporting/EMEP01_rv5.3_month.2022met_2022emis.nc"
            file = "EMEP01_rv5.3_month.2022met_2022emis.nc"
        elif year == 2023:
        # For 2023, use the specific file
            url = "https://thredds.met.no/thredds/fileServer/data/EMEP/2024_Reporting/EMEP01_rv5.3_month.2023met_2022emis.nc"
            file = "EMEP01_rv5.3_month.2023met_2022emis.nc"
        else:
            file = f"EMEP01_rv5.3_month.{year}met_{year}emis_rep2024.nc"
            url = base_url.format(year=year)

        output_path = os.path.join(output_dir, file)
        print(f"Downloading {url} to {output_path}")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"Downloaded {year}")
        else:
            print(f"Failed to download {year}: HTTP {response.status_code}")
else:
    print("no download requested")
#%%

catch_gdf =catch_gdf.to_crs("EPSG:4326").rename(columns={args.id: 'mvm_id'})


def load_year(year):
    """
    Load the EMEP data for a specific year.
    """
    if year == 2022:
        # For 2022, use the specific file
        file = r"EMEP01_rv5.3_month.2022met_2022emis.nc"
    elif year == 2023:
        # For 2023, use the specific file
        file = r"EMEP01_rv5.3_month.2023met_2022emis.nc"
    else:
        file = f"EMEP01_rv5.3_month.{year}met_{year}emis_rep2024.nc"
    
    file = os.path.join(output_dir, file)
    ds = rioxarray.open_rasterio(file).rio.write_crs("EPSG:4326")
    ds["TOT_S_DEP"] = ds.DDEP_SOX_m2Grid + ds.WDEP_SOX

    ds["TOT_N_DEP"] = ds.DDEP_OXN_m2Grid + ds.WDEP_OXN + ds.DDEP_RDN_m2Grid + ds.WDEP_RDN
    return ds

def get_vals(datarow,ds):

    # Clip the data for the geometry, keeping all time steps (months)
    s_clip = ds["TOT_S_DEP"].rio.clip([datarow.geometry], all_touched=True)
    n_clip = ds["TOT_N_DEP"].rio.clip([datarow.geometry], all_touched=True)

    # s_clip/n_clip shape: (time, y, x)
    # Compute spatial mean/median for each time (month), result: (time,)
    mean_S = np.nanmean(s_clip.values, axis=(1, 2))
    mean_N = np.nanmean(n_clip.values, axis=(1, 2))
    med_S = np.nanmedian(s_clip.values, axis=(1, 2))
    med_N = np.nanmedian(n_clip.values, axis=(1, 2))

    # Convert to kg/ha/yr (divide by 100), keep as arrays
    return pd.Series({
        'S_dep_mean_kg_ha_yr': mean_S / 100,
        'S_dep_med_kg_ha_yr': med_S / 100,
        'N_dep_mean_kg_ha_yr': mean_N / 100,
        'N_dep_med_kg_ha_yr': med_N / 100
    })

#%%
# For each year, load data, compute values for each catchment and month, and save to CSV

if len(catch_gdf) < 1000: 
    results = []
    for year in date_range:
        ds = load_year(year)
        for idx, row in catch_gdf.iterrows():
            try:
                vals = get_vals(row, ds)
                # vals are arrays of length 12 (months)
                for month in range(1, 13):
                    results.append({
                        'mvm_id': row['mvm_id'],
                        'S_dep_mean_kg_ha': vals['S_dep_mean_kg_ha_yr'][month-1],
                        'S_dep_med_kg_ha': vals['S_dep_med_kg_ha_yr'][month-1],
                        'N_dep_mean_kg_ha': vals['N_dep_mean_kg_ha_yr'][month-1],
                        'N_dep_med_kg_ha': vals['N_dep_med_kg_ha_yr'][month-1],
                        'year': year,
                        'month': month
                    })
            except Exception as e:
                print(f"Error processing mvm_id {row['mvm_id']} for year {year}: {e}")


    results_df = pd.DataFrame(results).rename(columns={'mvm_id' : args.id})
    results_df.to_csv(output_file, index=False)
    print(f"{year} saved to {output_file}")

else: 
    temp_dir = os.path.join(os.path.split(output_file)[1], "temp")
    os.makedirs(temp_dir, exist_ok=True)
    for year in date_range:   
        results = []
        ds = load_year(year)
        for idx, row in catch_gdf.iterrows():
            try:
                vals = get_vals(row, ds)
                # vals are arrays of length 12 (months)
                for month in range(1, 13):
                    results.append({
                        'mvm_id': row['mvm_id'],
                        'S_dep_mean_kg_ha': vals['S_dep_mean_kg_ha_yr'][month-1],
                        'S_dep_med_kg_ha': vals['S_dep_med_kg_ha_yr'][month-1],
                        'N_dep_mean_kg_ha': vals['N_dep_mean_kg_ha_yr'][month-1],
                        'N_dep_med_kg_ha': vals['N_dep_med_kg_ha_yr'][month-1],
                        'year': year,
                        'month': month
                    })
            except Exception as e:
                print(f"Error processing mvm_id {row['mvm_id']} for year {year}: {e}")

        out_file = os.path.join(temp_dir, f"emep_{year}.csv")
        results_df = pd.DataFrame(results).rename(columns={'mvm_id' : args.id})
        results_df.to_csv(out_file, index=False)
        print(f"Saved to {out_file}")
    
    dfs = []
    for filename in os.listdir(temp_dir):
        if filename.endswith(".csv"):
            file_path = os.path.join(temp_dir, filename)
            df = pd.read_csv(file_path)
            dfs.append(df)
    if dfs:
        result_df = pd.concat(dfs, ignore_index=True)
        result_df.to_csv(output_file, index=False)
        print(f"Concatenated file saved to {output_file}")
    else:
        print("No matching files found to concatenate.")
# %%
