# # Parse arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-f", type=str, help="folder for the the raster", default = "/mnt/gisdata_ivm/8_shared_files/Anna Lackner/PLC8_jordarter_reclassified.tif")
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-o", type=str, help="the output")

args = parser.parse_args()
#%%
import rasterstats as rs
import geopandas as gpd
import pandas as pd
import os

# Load catchments (polygons)
gdf_catch_sorted = gpd.read_file("../input/shapefile/catchments.zip").sort_values(by = 'Shape_Area', ascending = True)

gdf_catch = gdf_catch_sorted

# Path to raster
raster_path = "/mnt/gisdata_ivm/8_shared_files/Anna Lackner/PLC8_jordarter_reclassified.tif"

# Calculate zonal statistics (area for each class in the raster)
stats = rs.zonal_stats(gdf_catch, raster_path, stats="sum", band = 1, categorical  = True,  geojson_out = True)

# Display the results

print("done")

soil_dict = {
    0: "nodata",
    12: "cl",
    8: "cllm",
    4: "lm",
    2: "lmsd",
    1: "sd",
    10: "sdcl",
    7: "sdcllm",
    3: "sdlm",
    6: "sl",
    9: "slcllm",
    5: "sllm",
    11: "slcl"
}

out = pd.json_normalize(pd.DataFrame(stats)['properties']).rename(columns = soil_dict)

for col in soil_dict.values():
    if col in out.columns:  # Ensure the column exists in the DataFrame
        out[col] = out[col] / out['sum'] *100

out.to_csv("../results/PLC8/soil_type.csv")

# %%
