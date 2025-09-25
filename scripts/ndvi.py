#%% Only needed if used from terminal, otherwise the first block needs to be commented out
import argparse
from pathlib import Path
import os

parser = argparse.ArgumentParser()
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-o", type=str, help="the output folder")
parser.add_argument("-id", type=str, help="the id variable", default="mvm_id")
parser.add_argument("-log", type=str, help="log file", default="log")
parser.add_argument("-sy", type=int, help="start year", default=1990)
parser.add_argument("-ey", type=int, help="end year", default=2024)
args = parser.parse_args()

id_var = args.id
output_folder = args.o
cats_file = args.c

sy = args.sy
ey = args.ey

# Get the directory part of the log file path
log_dir = Path(args.log)
# Create the directory if it doesn't exist
log_dir.mkdir(parents=True, exist_ok=True)

#%% start logging 
from datetime import datetime
import logging
import sys

current_datetime = datetime.now().strftime("%Y_%m_%d")
str_current_datetime = str(current_datetime)
log_name =  os.path.join(log_dir, "log_NDVI_"+str_current_datetime+".txt")
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(log_name),
                        logging.StreamHandler()
                    ])

#%%

#%% connect to google earth engine

import ee
import geemap
# Authenticate
ee.Authenticate(auth_mode='localhost')
geemap.ee_initialize(project='ndvi-omdrev')
print(ee.String('Hello from the Earth Engine servers!').getInfo())
#%% acess shapefiles to be used

import os
import pandas as pd
import geopandas as gpd


if cats_file.endswith('.zip'):
    gdf_catch = gpd.read_file(f"zip://{cats_file}").to_crs("EPSG:4326")    
else:
    gdf_catch = gpd.read_file(cats_file).to_crs("EPSG:4326")

# gdf_catch.to_crs(epsg=4326, inplace=True)




logging.info("Loaded %d catchment polygons from %s", len(gdf_catch), cats_file)


#%%
import geopandas as gpd
from datetime import datetime

# # Initialize the Earth Engine API
# ee.Initialize()

# Function to calculate the last day of the month
def get_last_day_of_month(year, month):
    if month == "02":
        return f"{year}-{month}-29" if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else f"{year}-{month}-28"
    elif month in ["04", "06", "09", "11"]:
        return f"{year}-{month}-30"
    return f"{year}-{month}-31"

# Function to convert GeoDataFrame row to Earth Engine FeatureCollection
def geo_to_ee(gdf_row):
    geometry = gdf_row.geometry
    id = gdf_row[id_var]
    if geometry.geom_type == 'Polygon':
        ee_geom = ee.Geometry.Polygon(list(geometry.exterior.coords))
    elif geometry.geom_type == 'MultiPolygon':
        polygons = [ee.Geometry.Polygon(list(poly.exterior.coords)) for poly in geometry.geoms]
        ee_geom = ee.Geometry.MultiPolygon(polygons)
    elif geometry.geom_type == 'Point':
        ee_geom = ee.Geometry.Point([geometry.x, geometry.y])
    else:
        logging.error('Unsupported geometry %s',str(geometry.geom_type) )
        raise ValueError(f"Unsupported geometry type: {geometry.geom_type}")
    return ee.FeatureCollection([ee.Feature(ee_geom).set(id_var, id)])

# Function to compute NDVI statistics for a specific id
def process_id(gdf_row, years, months, Landsat_NDVI, output_dir):
    id = gdf_row[id_var]
    output_path = os.path.join(output_dir, f"NDVI_{id}.csv")

    if os.path.exists(output_path):
        logging.info("File %s already exists and is not empty. Skipping id: %s", output_path, id)
        return
    
    logging.info(f"Processing id: {id}")
    # Create (or touch) the output_path file so it exists, will be overwritten later
    with open(output_path, 'w') as f:
        pass


    shape = geo_to_ee(gdf_row)
    
    rows = []

    for year in years:
        for month in months:
            start_date = f"{year}-{month}-01"
            end_date = get_last_day_of_month(year, month)
            
            landsat_filtered = Landsat_NDVI \
                .filter(ee.Filter.date(start_date, end_date)) \
                .filterBounds(shape)
            
            image_count = landsat_filtered.size().getInfo()
            if image_count == 0:
                continue
            
            # Calculate statistics
            ndvi_min = landsat_filtered.reduce(ee.Reducer.min())
            ndvi_median = landsat_filtered.reduce(ee.Reducer.median())
            ndvi_max = landsat_filtered.reduce(ee.Reducer.max())

            
            stats_median = ndvi_median.reduceRegions(
                collection=shape,
                reducer=ee.Reducer.mean(),
                scale=30,
                tileScale=2
            )

            
            stats_min = ndvi_min.reduceRegions(
                collection=shape,
                reducer=ee.Reducer.mean(),
                scale=30,
                tileScale=2
            )
            
            stats_max = ndvi_max.reduceRegions(
                collection=shape,
                reducer=ee.Reducer.mean(),
                scale=30,
                tileScale=2
            )
            


            try:
                min_info = stats_min.getInfo()
                median_info = stats_median.getInfo()
                max_info = stats_max.getInfo()
                
                if 'features' in median_info and len(median_info['features']) > 0:
                    for i in range(len(median_info['features'])):
                        rows.append({
                            'month': month,
                            'year': year,
                            'id': id,
                            'NDVI_min': min_info['features'][i]['properties'].get('min', None),
                            'NDVI_median': median_info['features'][i]['properties'].get('mean', None),
                            'NDVI_max': max_info['features'][i]['properties'].get('mean', None),
                        })
            except Exception as e:
                    logging.error("Error processing stats for id {%s} (%s-%s): %s", str(id), str(year), str(month), e)
    
    if rows:
        pd.DataFrame(rows).to_csv(output_path, index=False)
        logging.info(f"Saved results for id %s to %s", str(id), output_path)
    else:
        logging.info("No valid NDVI data found for id %s.", str(id))

# Main processing loop
def main():
    output_dir = output_folder
    os.makedirs(output_dir, exist_ok=True)
    
    months = [  "05", "06", "07", "08", "09", "10"]
    years = list(range(sy, ey))
    Landsat_NDVI = ee.ImageCollection('LANDSAT/COMPOSITES/C02/T1_L2_8DAY_NDVI')
    
    for idx, gdf_row in gdf_catch.iterrows():
        try:
            process_id(gdf_row, years, months, Landsat_NDVI, output_dir)
        except Exception as e:
            logging.error("Error processing id %s: %s", str(gdf_row[id_var]), e)

if __name__ == "__main__":
    main()



#%% close logger
# Get the root logger (or any named logger if used)
logger = logging.getLogger()

# Iterate through all handlers and close them
for handler in logger.handlers[:]:  # Use a slice to clone the list while modifying
    handler.close()
    logger.removeHandler(handler)
# %%
