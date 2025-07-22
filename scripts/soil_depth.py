# Script for calculating soil depth
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-r", type=str,default = "default", help="the raster")
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-o", type=str, help="the output")

"""
Requires acess to the sgu soildepth raster.  
Inputs are: 
    - soil depth raster file location
    - catchments
    - output_folder
"""
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from rasterio.mask import mask
from rasterio.windows import Window
import contextily as ctx  # For basemap tiles
import os

# Paths to the raster and shapefile
args = parser.parse_args()

if args.r == "default":
    raster_path = r"\\gis.slu.se\gisdata\sgu\jorddjupsmodell\vector\epsg3006\2024-02-22\delivery\jorddjup_10x10m\jorddjup_10x10m.tif"
else: 
    raster_path = args.r


# Load the catchments that I am running it for
zip_catch = args.c



# Load the shapefiles from the ZIP files
gdf_catch = gpd.read_file(f"zip://{zip_catch}")



output_folder = args.o  # Folder to save maps



# Step 1: Read the shapefile (example)
gdf = gdf_catch.iloc[100:103] # Adjust for the number of catchments you want to process

# Step 2: Prepare to collect results and failures
statistics_results = []
failed_ids = []

# Process each shape in the catchment dataframe
for idx, zone in gdf.iterrows():
    try:
        # Extract the geometry and bounds of the current shape
        zone_geom = zone['geometry']
        bounds = zone_geom.bounds  # (min_x, min_y, max_x, max_y)

        # Open the raster file and process the data
        with rasterio.open(raster_path) as src:
            # Ensure shapefile CRS matches raster CRS
            if gdf.crs != src.crs:
                gdf = gdf.to_crs(src.crs)

            # Convert bounds to raster pixel coordinates
            col_start, row_start = ~src.transform * (bounds[0], bounds[1])  # min_x, min_y
            col_stop, row_stop = ~src.transform * (bounds[2], bounds[3])    # max_x, max_y

            # Ensure valid window bounds
            col_start, col_stop = sorted([int(max(0, min(src.width - 1, col_start))),
                                           int(max(0, min(src.width - 1, col_stop)))] )
            row_start, row_stop = sorted([int(max(0, min(src.height - 1, row_start))),
                                           int(max(0, min(src.height - 1, row_stop)))])
            
            # Define the window
            window = Window(col_start, row_start, col_stop - col_start, row_stop - row_start)

            # Read the raster data for the window
            raster_data = src.read(1, window=window)

            # # Plot the raster window and shapefile overlay
            # fig, ax = plt.subplots(figsize=(10, 10))
            
            # # Plot the raster with adjusted opacity (alpha controls transparency)
            # ax.imshow(raster_data, cmap='gray', extent=(bounds[0], bounds[2], bounds[3], bounds[1]), alpha=0.6)
            # ax.set_title(f"Catchment ID: {zone['mvm_id']}")  # Adjust ID field as necessary

            # # Overlay the current shape on the plot
            # gpd.GeoSeries(zone_geom).plot(ax=ax, facecolor='none', edgecolor='red', linewidth=2)
            
            # # Add a basemap using OpenStreetMap or Stamen Terrain
            # ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)  # OSM default basemap
            
            # # Save the map as an image file
            # map_filename = os.path.join(output_folder, f"{zone['mvm_id']}_map.png")
            # plt.savefig(map_filename, dpi=300)
            # plt.close()

            # Mask the raster data using the current geometry
            out_image, out_transform = mask(src, [zone_geom], crop=True)

            # Extract valid raster values and calculate statistics
            masked_values = out_image[0]
            masked_values = masked_values[masked_values != src.nodata]

            if len(masked_values) > 0:
                statistics_results.append({
                    'mvm_id': zone['mvm_id'],  # Adjust to your zone ID field
                    'mean': np.mean(masked_values),
                    'stddev': np.std(masked_values),
                    'min': np.min(masked_values),
                    'max': np.max(masked_values),
                    '25th_percentile': np.percentile(masked_values, 25),
                    '75th_percentile': np.percentile(masked_values, 75)
                })
            else:
                failed_ids.append(zone['mvm_id'])

    except Exception as e:
        # If an error occurs, log the failure ID and continue
        print(f"Failed to process {zone['mvm_id']}: {e}")
        failed_ids.append(zone['mvm_id'])

# Step 3: Save statistics to CSV
statistics_df = pd.DataFrame(statistics_results)
statistics_df.to_csv(output_folder, index=False)

# Step 4: Log failed IDs to a text file
with open(os.path.join(os.path.split(output_folder)[0], "failed_soil_depth.txt"), 'w') as f:
    for failed_id in failed_ids:
        f.write(f"{failed_id}\n")

print(f"Processing complete. Statistics saved to {output_folder}, and failed IDs saved to failed.txt.")
