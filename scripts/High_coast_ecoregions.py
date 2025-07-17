#%%
# Parse arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-hk", type=str, help="file for the high coast shp")
parser.add_argument("-eco", type=str, help="file for the high coast shp")
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-o", type=str, help="the output")


args = parser.parse_args()
file_catch = args.c
output_file = args.o
file_HK = args.hk
file_ER = args.eco

#%%

# packages needed to run discharge application 
from shapely.geometry import Polygon
import os
import geopandas as gpd
from shapely.geometry import mapping
import pandas as pd
import numpy as np
# %%

if file_HK.endswith('.shp'):
    HK = gpd.read_file(file_HK) # HK = 1 is the area underneath the high coast 
elif file_HK.endswith('.zip'):
    HK = gpd.read_file(f"zip://{file_HK}")
else:
    file_HK = "~/mnt/anna/My Documents/04_Projects/09_General/01_GIS/HK.shp"
    HK = gpd.read_file(file_HK)

if file_ER.endswith('.shp'):
    ER = gpd.read_file(file_ER)
elif file_ER.endswith('.zip'):
    ER = gpd.read_file(f"zip://{file_ER}")
else:
    file_ER = "~/mnt/anna/My Documents/04_Projects/09_General/01_GIS/ekoreg_2006_sweref99.shp"
    ER = gpd.read_file(file_ER)
# output_file = "../results/high_coast_ecoregions_merged.csv"
# file_catch = "~/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/02_raw_data/catchments/merged_catchments/merged_catchments.shp"

#%%
if file_catch.endswith('.shp'):
    cats = gpd.read_file(file_catch)
elif file_catch.endswith('.zip'):
    cats = gpd.read_file(f"zip://{file_catch}")
else:
    raise ValueError("Catchment file must be a .shp or .zip file.")

#%%

# Filter HK polygons where HK == 1
HK_1 = HK[HK['HK'] == 1]

# Spatial intersection between catchments and HK == 1 polygons
intersect = gpd.overlay(cats, HK_1, how='intersection')

# Calculate area of intersection
intersect['intersect_area'] = intersect.geometry.area

# Sum intersected area for each catchment (mvm_id)
intersect_sum = intersect.groupby('mvm_id')['intersect_area'].sum().reset_index()

# Calculate original catchment area
cats['catch_area'] = cats.geometry.area

# Merge summed intersection area with catchments
result = cats[['mvm_id', 'catch_area']].merge(intersect_sum, on='mvm_id', how='left')

# Fill NaN (no overlap) with 0
result['intersect_area'] = result['intersect_area'].fillna(0)

# Calculate percentage of each catchment within HK == 1
result['pct_in_HK1'] = result['intersect_area'] / result['catch_area'] * 100

# Keep only mvm_id and percentage
result = result[['mvm_id', 'pct_in_HK1']]
result = result.rename(columns={'pct_in_HK1': 'pct_below_HK'})

#%%

# ER.plot()

# Spatial join to find ecoregions for each catchment given in the column in ekoreg of ER. 
# A catchment might overlap multiple ecoregions, we want to know which one has the greatest coverage and add to results

# Perform intersection between catchments and ecoregions
catch_ecoreg = gpd.overlay(cats, ER, how='intersection')

# Calculate area of intersection
catch_ecoreg['intersect_area'] = catch_ecoreg.geometry.area

# For each catchment, find the ecoregion with the largest intersection area
idx = catch_ecoreg.groupby('mvm_id')['intersect_area'].idxmax()
dominant_ecoreg = catch_ecoreg.loc[idx, ['mvm_id', 'ekoreg']].reset_index(drop=True)

# Merge dominant ecoregion info into result DataFrame
result_both = result.merge(dominant_ecoreg, on='mvm_id', how='left')

#%%
# use x_utlopp and y_utlopp as Sweref tm 99 coordinates (same as all otehr spatial crs system used) to find the ecoregion of the outlet and also add it to the results
outlets = cats[['mvm_id', 'x_utlopp', 'y_utlopp']].dropna()
# Convert outlets DataFrame to GeoDataFrame using x and y as coordinates
outlets = outlets.rename(columns={'x_utlopp': 'x', 'y_utlopp': 'y'})
outlets_gdf = gpd.GeoDataFrame(
    outlets,
    geometry=gpd.points_from_xy(outlets['x'], outlets['y']),
    crs=cats.crs
)
# Perform spatial join to find ecoregions for each outlet
outlet_ecoreg = gpd.sjoin(outlets_gdf, ER, how='left', predicate='intersects')
# Select relevant columns and rename for clarity
outlet_ecoreg = outlet_ecoreg[['mvm_id', 'ekoreg']].rename(columns={'ekoreg': 'outlet_ekoreg'})
# Merge outlet ecoregion info into result DataFrame
result_both = result_both.merge(outlet_ecoreg, on='mvm_id', how='left')

#%%


result_both = result_both.drop(columns=['outlet_ekoreg'])

print(result_both.isna().sum())  # Check for NA values in the result DataFrame
# %%
# Plot the results, fiorst merge back to cats and then make a plot with 2 figures once the cats color codded by HK and once with the ecoregions
cats_results = cats.merge(result_both, on='mvm_id', how='left')
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(12, 8))

# Plot 1: Catchments colored by pct_in_HK1
cats_results.plot(column='pct_below_HK', cmap='viridis', legend=True, ax=axes[0])
axes[0].set_title('Catchments: % in High Coast')

# Plot 2: Catchments colored by dominant ecoregion
cats_results.plot(column='ekoreg', cmap='Set3', legend=True, ax=axes[1])
axes[1].set_title('Catchments: Dominant Ecoregion')


for ax in axes:
    ax.axis('off')

plt.tight_layout()
plt.show()
# %%
result_both.to_csv(output_file, index=False)