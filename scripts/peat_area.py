# Script for calculating peat area
#%% Only needed if used from terminal, otherwise the first block needs to be commented out
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("r", type=str, help="the raster")
parser.add_argument("c", type=str, help="the catchments")
parser.add_argument("o", type=str, help="the output")
args = parser.parse_args()
# %%
import rasterstats as rs
import geopandas as gpd
import pandas as pd


# Load catchments (polygons)
gdf_catch = gpd.read_file("zip://DOC_catchments//input/shapefile/catchments.zip")

mvm_ids = [ 1815, 1329 ]

gdf_catch = gdf_catch.loc[gdf_catch['mvm_id'].isin(mvm_ids)]

# gdf_catch = gpd.read_file(args.c)


## Need to mount network drive to gis. 

# Path to raster
raster_path = r"\\gis.slu.se\gisdata\slu\Torvkarta_1_0\Klassad_torvkarta\ClassifiedPeatMap.tif"

# Calculate zonal statistics (area for each class in the raster)
stats = rs.zonal_stats(gdf_catch, raster_path, stats="sum", band = 1, categorical  = True,  geojson_out = True)

# Display the results
print("done")

out = pd.json_normalize(pd.DataFrame(stats)['properties'])
out['sum'] = pd.to_numeric(out['sum'], errors = 'coerce')
out['Shape_Area'] = pd.to_numeric(out['Shape_Area'], errors = 'coerce')
out['coverage'] = out['Shape_Area']/(4 * out['sum']) * 100

out
# out.to_csv('peat_area_by_class_all.csv')
# %%
